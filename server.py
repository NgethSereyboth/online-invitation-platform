"""Credential-free development backend for E-invitation-website."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs, quote
from pathlib import Path
import argparse, base64, hashlib, hmac, html, io, ipaddress, json, os, re, secrets, sqlite3, time, uuid, threading, smtplib, ssl, mimetypes, urllib.request, urllib.error, subprocess, shlex, shutil, warnings, zipfile, signal, sys
from http.cookies import SimpleCookie
from html.parser import HTMLParser
from contextlib import contextmanager
from email.message import EmailMessage
from email.utils import formatdate
from security_v13 import (ARGON2_AVAILABLE, hash_password as account_hash_password, verify_password as account_verify_password, new_csrf_token, new_totp_secret, verify_totp, otpauth_uri, b64url, b64url_decode, parse_attestation_object, cose_ec2_to_pem, verify_es256_signature, verify_client_data, parse_assertion_auth_data)
from typography_contract import normalize_font_id, finite_number
from typography_document_model import normalize_document_typography
from rich_text_document_model import normalize_document_rich_text
from document_schema_v32 import normalize_document_v32
from ai_agent import AgentConfig, AgentService, AgentServiceError, ensure_agent_schema, tool_catalog
from platform_v32 import PlatformConfig, PlatformService, PlatformServiceError, ensure_personal_workspace, ensure_platform_schema
from future_platform_v52 import FuturePlatformService, FuturePlatformError, ensure_future_schema



def platform_env(name, default=None):
    """Read the current EINVITE_* setting, with legacy SOVAN_* fallback."""
    legacy = name.replace("EINVITE_", "SOVAN_", 1)
    return os.environ.get(name, os.environ.get(legacy, default))

ROOT = Path(__file__).resolve().parent
DATA = Path(platform_env("EINVITE_DATA_DIR", str(ROOT / "data"))).expanduser().resolve()
UPLOADS = DATA / "uploads"
IMAGE_CACHE = DATA / "image-cache"
QUARANTINE = DATA / "quarantine"
SOCIAL_CACHE = DATA / "social-cache"
BACKUPS = DATA / "backups"
DB = DATA / "invites.db"
OBJECT_STORAGE_BUCKET = platform_env("EINVITE_OBJECT_STORAGE_BUCKET", "").strip()
OBJECT_STORAGE_ENDPOINT = platform_env("EINVITE_OBJECT_STORAGE_ENDPOINT", "").strip() or None
OBJECT_STORAGE_REGION = platform_env("EINVITE_OBJECT_STORAGE_REGION", "auto").strip() or "auto"
OBJECT_STORAGE_ACCESS_KEY = platform_env("EINVITE_OBJECT_STORAGE_ACCESS_KEY", "").strip() or None
OBJECT_STORAGE_SECRET_KEY = platform_env("EINVITE_OBJECT_STORAGE_SECRET_KEY", "").strip() or None
OBJECT_STORAGE_PREFIX = platform_env("EINVITE_OBJECT_STORAGE_PREFIX", "materials/").strip().strip("/")
OBJECT_STORAGE_PUBLIC_BASE_URL = platform_env("EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL", "").strip().rstrip("/")
MEDIA_URL_TTL_SECONDS = max(60, min(3600, int(platform_env("EINVITE_MEDIA_URL_TTL_SECONDS", "900"))))
IMAGE_WIDTH_ALLOWLIST = (320, 480, 768, 960, 1440, 1920)
IMAGE_FORMAT_ALLOWLIST = {"webp", "jpeg", "jpg", "png", "avif"}
MAX_IMAGE_DIMENSION = max(2048, min(30000, int(platform_env("EINVITE_MAX_IMAGE_DIMENSION", "12000"))))
MAX_IMAGE_MEGAPIXELS = max(10, min(120, int(platform_env("EINVITE_MAX_IMAGE_MEGAPIXELS", "40"))))
IMAGE_CACHE_MAX_BYTES = max(50_000_000, int(platform_env("EINVITE_IMAGE_CACHE_MAX_BYTES", "536870912")))
IMAGE_CACHE_MAX_FILES = max(100, int(platform_env("EINVITE_IMAGE_CACHE_MAX_FILES", "5000")))
MALWARE_SCANNER_COMMAND = platform_env("EINVITE_MALWARE_SCANNER_COMMAND", "").strip()
MALWARE_SCANNER_MODE = platform_env("EINVITE_MALWARE_SCANNER_MODE", "").strip().lower()
REQUIRE_MALWARE_SCAN = platform_env("EINVITE_REQUIRE_MALWARE_SCAN", "0").lower() in {"1", "true", "yes"}
MALWARE_SCAN_TIMEOUT_SECONDS = max(10, min(300, int(platform_env("EINVITE_MALWARE_SCAN_TIMEOUT_SECONDS", "120"))))
MATERIAL_IMPORT_MAX_ARCHIVE_BYTES = max(10_000_000, min(500_000_000, int(platform_env("EINVITE_MATERIAL_IMPORT_MAX_ARCHIVE_BYTES", "100000000"))))
MATERIAL_IMPORT_MAX_UNCOMPRESSED_BYTES = max(25_000_000, min(2_000_000_000, int(platform_env("EINVITE_MATERIAL_IMPORT_MAX_UNCOMPRESSED_BYTES", "500000000"))))
MATERIAL_IMPORT_MAX_ENTRIES = max(100, min(10000, int(platform_env("EINVITE_MATERIAL_IMPORT_MAX_ENTRIES", "2000"))))
MATERIAL_IMPORT_MAX_ENTRY_BYTES = max(15_000_000, min(100_000_000, int(platform_env("EINVITE_MATERIAL_IMPORT_MAX_ENTRY_BYTES", "50000000"))))
MATERIAL_IMPORT_MAX_COMPRESSION_RATIO = max(20, min(1000, int(platform_env("EINVITE_MATERIAL_IMPORT_MAX_COMPRESSION_RATIO", "250"))))
STRIP_EXIF_DERIVATIVES = platform_env("EINVITE_STRIP_EXIF_DERIVATIVES", "1").lower() in {"1", "true", "yes"}
_S3_CLIENT = None
_MALWARE_SCANNER_PROBE = None
_MALWARE_SCANNER_PROBE_LOCK = threading.Lock()

DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)
IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
QUARANTINE.mkdir(parents=True, exist_ok=True)
SOCIAL_CACHE.mkdir(parents=True, exist_ok=True)
BACKUPS.mkdir(parents=True, exist_ok=True)

def persistent_data_secret(env_name, filename):
    configured=platform_env(env_name,"").strip()
    if configured:return configured
    path=DATA/filename
    try:
        if path.is_file():return path.read_text(encoding="utf-8").strip()
        value=secrets.token_urlsafe(48);path.write_text(value,encoding="utf-8")
        try:os.chmod(path,0o600)
        except OSError:pass
        return value
    except OSError:
        return secrets.token_urlsafe(48)

GUEST_TOKEN_SECRET=persistent_data_secret("EINVITE_GUEST_TOKEN_SECRET",".guest-token-secret")

# Deployment mode must be explicit. A public base URL is also required by the
# local launcher so invitations can generate working preview/share links; it
# does not, by itself, mean that the process is a production deployment.
PRODUCTION_MODE = platform_env("EINVITE_PRODUCTION", "0").lower() in {"1","true","yes"}
STRICT_SESSION_CSRF = PRODUCTION_MODE or platform_env("EINVITE_STRICT_SESSION_CSRF", "0").lower() in {"1","true","yes"}
DISCLOSE_HEALTH_DETAILS = platform_env("EINVITE_DISCLOSE_HEALTH_DETAILS", "0" if PRODUCTION_MODE else "1").lower() in {"1","true","yes"}
ALLOW_LOCAL_ADMIN_BOOTSTRAP = not PRODUCTION_MODE and platform_env("EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP", "1").lower() in {"1","true","yes"}
_UPLOAD_SECRET_CONFIGURED = platform_env("EINVITE_UPLOAD_SIGNING_SECRET", "").strip()
_MEDIA_SECRET_CONFIGURED = platform_env("EINVITE_MEDIA_SIGNING_SECRET", "").strip()
if PRODUCTION_MODE and (not _UPLOAD_SECRET_CONFIGURED or not _MEDIA_SECRET_CONFIGURED):
    raise RuntimeError(
        "Production startup requires stable EINVITE_UPLOAD_SIGNING_SECRET and "
        "EINVITE_MEDIA_SIGNING_SECRET values. Configure both secrets before starting the server."
    )
UPLOAD_SIGNING_SECRET = _UPLOAD_SECRET_CONFIGURED or persistent_data_secret("EINVITE_UPLOAD_SIGNING_SECRET", ".upload-signing-secret")
MEDIA_SIGNING_SECRET = _MEDIA_SECRET_CONFIGURED or persistent_data_secret("EINVITE_MEDIA_SIGNING_SECRET", ".media-signing-secret")
UPLOAD_SIGNING_PREVIOUS_SECRETS = tuple(x.strip() for x in platform_env("EINVITE_UPLOAD_SIGNING_PREVIOUS_SECRETS", "").split(",") if x.strip())
MEDIA_SIGNING_PREVIOUS_SECRETS = tuple(x.strip() for x in platform_env("EINVITE_MEDIA_SIGNING_PREVIOUS_SECRETS", "").split(",") if x.strip())

RATE_BUCKETS = {}
RATE_LOCK = threading.Lock()
STUDIO_BACKUP_LOCKS = {}
STUDIO_BACKUP_LOCKS_GUARD = threading.Lock()

PLAN_LIMITS = {
    "free": {"invitations": 3, "templates": 5, "storageBytes": 250_000_000, "bandwidthBytes30d": 2_000_000_000},
    "creator": {"invitations": 50, "templates": 100, "storageBytes": 5_000_000_000, "bandwidthBytes30d": 50_000_000_000},
    "studio": {"invitations": 500, "templates": 1000, "storageBytes": 50_000_000_000, "bandwidthBytes30d": 500_000_000_000},
}
PLAN_LIMITS_ENFORCED = platform_env("EINVITE_ENFORCE_PLAN_LIMITS", "0").lower() in {"1", "true", "yes"}

BACKGROUND_MEDIA_ENABLED = platform_env("EINVITE_BACKGROUND_MEDIA", "0").lower() in {"1","true","yes"}
OBJECT_STORAGE_KMS_KEY_ID = platform_env("EINVITE_OBJECT_STORAGE_KMS_KEY_ID", "").strip()
OBJECT_STORAGE_VERSIONING_EXPECTED = platform_env("EINVITE_OBJECT_STORAGE_VERSIONING", "0").lower() in {"1","true","yes"}
MEDIA_TRASH_DAYS = max(1, int(platform_env("EINVITE_MEDIA_TRASH_DAYS", "30") or 30))
BANDWIDTH_WINDOW_MS = 30*24*60*60*1000
MESSAGING_WEBHOOK_ENDPOINT = platform_env("EINVITE_MESSAGING_WEBHOOK_ENDPOINT", "").strip()
MESSAGING_WEBHOOK_SECRET = platform_env("EINVITE_MESSAGING_WEBHOOK_SECRET", "").strip()
CUSTOM_DOMAIN_SUFFIX_ALLOWLIST = [x.strip().lower() for x in platform_env("EINVITE_CUSTOM_DOMAIN_SUFFIX_ALLOWLIST", "").split(",") if x.strip()]
STARTED_AT = time.time()
PRESENCE_LOCK=threading.Lock()
PRESENCE_STATE={}


def current_presence(invite_id):
    """Return current presence rows from Redis or the in-process fallback."""
    now=int(time.time()*1000);items=[];client=redis_client()
    if client:
        try:
            for key in client.scan_iter(match=f"einvite:presence:{invite_id}:*"):
                raw=client.get(key)
                if raw:
                    value=json.loads(raw);items.append(value)
        except Exception:
            items=[]
    if not items:
        with PRESENCE_LOCK:
            cutoff=now-60_000
            for key,value in list(PRESENCE_STATE.items()):
                if value.get("updatedAt",0)<cutoff:PRESENCE_STATE.pop(key,None)
            items=[dict(value) for (iid,_,_),value in PRESENCE_STATE.items() if iid==invite_id and value.get("updatedAt",0)>cutoff]
    dedup={f"{x.get('userId')}:{x.get('clientId')}":x for x in items}
    return list(dedup.values())
SESSION_COOKIE_NAME = platform_env("EINVITE_SESSION_COOKIE_NAME", "einvite_session").strip() or "einvite_session"
COOKIE_SECURE = platform_env("EINVITE_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
DEV_AUTH_TOKENS_ENABLED = platform_env("EINVITE_DEV_AUTH_TOKENS", "0").lower() in {"1", "true", "yes"}
AI_ENDPOINT = platform_env("EINVITE_AI_ENDPOINT", "").strip()
AI_API_KEY = platform_env("EINVITE_AI_API_KEY", "").strip()
AI_MODEL = platform_env("EINVITE_AI_MODEL", "").strip()
AI_TIMEOUT = max(2, min(60, int(platform_env("EINVITE_AI_TIMEOUT", "20"))))
BILLING_WEBHOOK_SECRET = platform_env("EINVITE_BILLING_WEBHOOK_SECRET", "").strip()
BILLING_CHECKOUT_ENDPOINT = platform_env("EINVITE_BILLING_CHECKOUT_ENDPOINT", "").strip()
BILLING_API_KEY = platform_env("EINVITE_BILLING_API_KEY", "").strip()
BILLING_PROVIDER_NAME = platform_env("EINVITE_BILLING_PROVIDER_NAME", "Secure card checkout").strip() or "Secure card checkout"
BILLING_CURRENCY = platform_env("EINVITE_BILLING_CURRENCY", "USD").strip().upper()
if BILLING_CURRENCY not in {"USD", "KHR"}: BILLING_CURRENCY = "USD"
BILLING_PLAN_PRICES = {
    "creator": max(0, int(platform_env("EINVITE_CREATOR_PRICE_MINOR", "900"))),
    "studio": max(0, int(platform_env("EINVITE_STUDIO_PRICE_MINOR", "2400"))),
}
JSON_LOGS = platform_env("EINVITE_JSON_LOGS", "0").lower() in {"1", "true", "yes"}
REDIS_URL = platform_env("EINVITE_REDIS_URL", "").strip()
_REDIS_CLIENT = None
DATABASE_URL = platform_env("EINVITE_DATABASE_URL", "").strip()
DATABASE_KIND = "postgresql" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"
PUBLIC_BASE_URL = platform_env("EINVITE_PUBLIC_BASE_URL", "").strip().rstrip("/")
TRUSTED_PROXY_IPS = {x.strip() for x in platform_env("EINVITE_TRUSTED_PROXY_IPS", "").split(",") if x.strip()}
ALLOWED_HOSTS = {x.strip().lower().rstrip(".") for x in platform_env("EINVITE_ALLOWED_HOSTS", "").split(",") if x.strip()}
REQUEST_SOCKET_TIMEOUT_SECONDS = max(5, min(300, int(platform_env("EINVITE_REQUEST_SOCKET_TIMEOUT_SECONDS", "45"))))
MAX_CONCURRENT_REQUESTS = max(8, min(512, int(platform_env("EINVITE_MAX_CONCURRENT_REQUESTS", "64"))))
ACCOUNT_TRASH_DAYS = max(1, min(365, int(platform_env("EINVITE_ACCOUNT_TRASH_DAYS", "30"))))
AUDIT_RETENTION_DAYS = max(30, min(3650, int(platform_env("EINVITE_AUDIT_RETENTION_DAYS", "730"))))
BOT_PROTECTION_ENDPOINT = platform_env("EINVITE_BOT_PROTECTION_ENDPOINT", "").strip()
BOT_PROTECTION_SECRET = platform_env("EINVITE_BOT_PROTECTION_SECRET", "").strip()
PASSKEY_RP_NAME = platform_env("EINVITE_PASSKEY_RP_NAME", "E-invitation-website").strip() or "E-invitation-website"
REQUIRE_VERIFIED_EMAIL = platform_env("EINVITE_REQUIRE_VERIFIED_EMAIL", "1" if PRODUCTION_MODE else "0").lower() in {"1","true","yes"}

def redis_client():
    global _REDIS_CLIENT
    if not REDIS_URL:return None
    if _REDIS_CLIENT is not None:return _REDIS_CLIENT
    try:
        import redis
        _REDIS_CLIENT=redis.Redis.from_url(REDIS_URL,decode_responses=True,socket_timeout=2)
        _REDIS_CLIENT.ping()
        return _REDIS_CLIENT
    except Exception as exc:
        print(f"Redis unavailable; using in-memory rate limits: {exc}",flush=True)
        _REDIS_CLIENT=False
        return None


def send_platform_email(to_email, subject, text_body):
    """Send transactional mail through optional SMTP configuration.

    Required environment variables for delivery: EINVITE_SMTP_HOST and EINVITE_MAIL_FROM.
    Optional: EINVITE_SMTP_PORT (587), EINVITE_SMTP_USER, EINVITE_SMTP_PASSWORD,
    EINVITE_SMTP_TLS (1), and EINVITE_SMTP_SSL (0).
    """
    host=platform_env("EINVITE_SMTP_HOST","").strip();sender=platform_env("EINVITE_MAIL_FROM","").strip()
    if not host or not sender:return False
    port=int(platform_env("EINVITE_SMTP_PORT","587"));user=platform_env("EINVITE_SMTP_USER","");password=platform_env("EINVITE_SMTP_PASSWORD","")
    use_ssl=platform_env("EINVITE_SMTP_SSL","0").lower() in {"1","true","yes"};use_tls=platform_env("EINVITE_SMTP_TLS","1").lower() in {"1","true","yes"}
    message=EmailMessage();message["From"]=sender;message["To"]=to_email;message["Subject"]=subject;message.set_content(text_body)
    if use_ssl:
        with smtplib.SMTP_SSL(host,port,timeout=15,context=ssl.create_default_context()) as smtp:
            if user:smtp.login(user,password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host,port,timeout=15) as smtp:
            smtp.ehlo()
            if use_tls:smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            if user:smtp.login(user,password)
            smtp.send_message(message)
    return True

def security_notification(email,subject,detail):
    """Best-effort security notification; delivery requires configured SMTP."""
    if not email:return False
    try:return bool(send_platform_email(email,subject,f"{detail}\n\nIf this was not you, open Account Security and revoke other sessions immediately."))
    except Exception:return False

def auth_action_url(path, token):
    base=platform_env("EINVITE_PUBLIC_BASE_URL","").rstrip("/")
    return f"{base}{path}?token={token}" if base else f"{path}?token={token}"

def object_storage_enabled():
    return bool(OBJECT_STORAGE_BUCKET)

def object_storage_key(path, owner_id=""):
    clean=str(path or "").lstrip("/")
    tenant=f"owners/{clean_slug(owner_id)}/" if owner_id else ""
    key=f"{tenant}{clean}"
    return f"{OBJECT_STORAGE_PREFIX}/{key}" if OBJECT_STORAGE_PREFIX else key

def stored_object_storage_key(path):
    clean=Path(str(path or "")).name
    if not clean:return ""
    try:
        with connect() as db:
            row=db.execute("SELECT storage_key FROM stored_objects WHERE path=? ORDER BY created_at DESC LIMIT 1",(clean,)).fetchone()
        if row and row["storage_key"]:return row["storage_key"]
    except Exception:pass
    return object_storage_key(clean)

def object_storage_client():
    global _S3_CLIENT
    if _S3_CLIENT is not None:return _S3_CLIENT
    if not object_storage_enabled():return None
    try:import boto3
    except ImportError as exc:raise RuntimeError("Object storage is configured but boto3 is not installed. Install requirements-production.txt.") from exc
    kwargs={"service_name":"s3","region_name":OBJECT_STORAGE_REGION}
    if OBJECT_STORAGE_ENDPOINT:kwargs["endpoint_url"]=OBJECT_STORAGE_ENDPOINT
    if OBJECT_STORAGE_ACCESS_KEY:kwargs["aws_access_key_id"]=OBJECT_STORAGE_ACCESS_KEY
    if OBJECT_STORAGE_SECRET_KEY:kwargs["aws_secret_access_key"]=OBJECT_STORAGE_SECRET_KEY
    _S3_CLIENT=boto3.client(**kwargs);return _S3_CLIENT

def asset_public_url(path):
    """Return a first-party media URL.

    Storage is private by default. Even when R2/S3 is configured, invitation
    documents use the application media gateway so authorization rules remain
    consistent between local and production deployments.
    """
    return f"/uploads/{quote(Path(str(path or '')).name,safe='')}"

def responsive_asset_url(path):
    return f"/api/image/{quote(Path(str(path or '')).name,safe='')}"

def store_asset_bytes(path,raw,mime,owner_id=""):
    clean=Path(str(path or "")).name
    key=object_storage_key(clean,owner_id)
    if object_storage_enabled():
        params={"Bucket":OBJECT_STORAGE_BUCKET,"Key":key,"Body":raw,"ContentType":mime,"CacheControl":"private,max-age=0,no-store"}
        if OBJECT_STORAGE_KMS_KEY_ID:params.update(ServerSideEncryption="aws:kms",SSEKMSKeyId=OBJECT_STORAGE_KMS_KEY_ID)
        else:params.update(ServerSideEncryption="AES256")
        object_storage_client().put_object(**params)
    else:(UPLOADS/clean).write_bytes(raw)
    return key

def purge_derivative_cache(path, source_hash=""):
    clean=Path(str(path or "")).name
    tag=str(source_hash or "")[:20]
    if not clean:return
    for width in IMAGE_WIDTH_ALLOWLIST:
        for fmt,suffix in (("webp",".webp"),("jpeg",".jpg"),("jpg",".jpg"),("png",".png"),("avif",".avif")):
            if not tag:continue
            key=hashlib.sha256(f"{clean}|{tag}|{width}|{fmt}".encode()).hexdigest()
            target=IMAGE_CACHE/(key+suffix)
            try:
                if target.is_file():target.unlink()
            except OSError:pass

def delete_stored_asset(path, source_hash=""):
    clean=Path(str(path or "")).name
    if not clean:return
    if object_storage_enabled():
        try:object_storage_client().delete_object(Bucket=OBJECT_STORAGE_BUCKET,Key=stored_object_storage_key(clean))
        except Exception as exc:print(f"Object-storage delete failed for {clean}: {exc}",flush=True)
    else:
        local=UPLOADS/clean
        if local.exists():local.unlink()
    purge_derivative_cache(clean,source_hash)

def read_stored_asset_bytes(path):
    clean=Path(str(path or "")).name
    if not clean:return None
    if object_storage_enabled():
        try:return object_storage_client().get_object(Bucket=OBJECT_STORAGE_BUCKET,Key=stored_object_storage_key(clean))["Body"].read()
        except Exception:return None
    local=UPLOADS/clean
    return local.read_bytes() if local.is_file() else None

def media_signature(path, invitation_id, expires):
    clean=Path(str(path or "")).name
    payload=f"{clean}|{invitation_id}|{int(expires)}"
    return hmac.new(MEDIA_SIGNING_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()

def signed_media_url(path, invitation_id, expires=None):
    expires=int(expires or (time.time()+MEDIA_URL_TTL_SECONDS))
    clean=Path(str(path or "")).name
    signature=media_signature(clean,invitation_id,expires)
    return f"/api/media/{quote(clean,safe='')}?i={quote(str(invitation_id),safe='')}&exp={expires}&sig={signature}"

def verify_media_signature(path, invitation_id, expires, signature):
    try:expires=int(expires)
    except (TypeError,ValueError):return False
    if expires<int(time.time()) or expires>int(time.time())+86400:return False
    clean=Path(str(path or "")).name;payload=f"{clean}|{invitation_id}|{int(expires)}";provided=str(signature or "")
    for secret in (MEDIA_SIGNING_SECRET,*MEDIA_SIGNING_PREVIOUS_SECRETS):
        expected=hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()
        if hmac.compare_digest(provided,expected):return True
    return False

def windows_defender_cli():
    """Return the newest Microsoft Defender command-line scanner on Windows."""
    if os.name != "nt":return None
    candidates=[]
    program_data=os.environ.get("ProgramData","")
    if program_data:
        platform_dir=Path(program_data)/"Microsoft"/"Windows Defender"/"Platform"
        if platform_dir.is_dir():
            try:
                candidates.extend((item/"MpCmdRun.exe" for item in sorted(platform_dir.iterdir(),reverse=True) if item.is_dir()))
            except OSError:pass
    program_files=os.environ.get("ProgramFiles","")
    if program_files:candidates.append(Path(program_files)/"Windows Defender"/"MpCmdRun.exe")
    discovered=shutil.which("MpCmdRun.exe")
    if discovered:candidates.append(Path(discovered))
    return next((str(item) for item in candidates if item.is_file()),None)

def split_scanner_command(value):
    parts=shlex.split(str(value or ""),posix=os.name!="nt")
    if os.name=="nt":parts=[part[1:-1] if len(part)>1 and part[0]==part[-1] and part[0] in {'\"',"'"} else part for part in parts]
    return parts

def malware_scan_command(path):
    if MALWARE_SCANNER_COMMAND:return split_scanner_command(MALWARE_SCANNER_COMMAND)+[str(path)]
    defender=windows_defender_cli() if MALWARE_SCANNER_MODE=="windows-defender" else None
    return [defender,"-Scan","-ScanType","3","-File",str(path),"-DisableRemediation"] if defender else None

def malware_scanner_status(probe=False):
    global _MALWARE_SCANNER_PROBE
    mode="command" if MALWARE_SCANNER_COMMAND else "windows-defender" if MALWARE_SCANNER_MODE=="windows-defender" else "none"
    configured=bool(MALWARE_SCANNER_COMMAND or (mode=="windows-defender" and windows_defender_cli()))
    if not probe or not configured:return {"mode":mode,"ready":configured,"required":REQUIRE_MALWARE_SCAN}
    with _MALWARE_SCANNER_PROBE_LOCK:
        if _MALWARE_SCANNER_PROBE is None:
            temp=QUARANTINE/f"scanner-probe-{uuid.uuid4().hex}.txt"
            try:
                temp.write_bytes(b"E-invitation malware scanner readiness probe")
                command=malware_scan_command(temp)
                result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=MALWARE_SCAN_TIMEOUT_SECONDS) if command else None
                _MALWARE_SCANNER_PROBE=bool(result and result.returncode==0)
            except (OSError,subprocess.SubprocessError):_MALWARE_SCANNER_PROBE=False
            finally:
                try:temp.unlink(missing_ok=True)
                except OSError:pass
    return {"mode":mode,"ready":bool(_MALWARE_SCANNER_PROBE),"required":REQUIRE_MALWARE_SCAN}

def scan_material_bytes(raw, mime, name="upload"):
    """Optional malware-scanning abstraction.

    A configured command receives the quarantined filename as its final argument
    and must exit with status 0 for a clean file. Laptop hosting uses Microsoft
    Defender and fails closed when the scanner is unavailable.
    """
    scanner_status=malware_scanner_status(probe=True)
    if not scanner_status["ready"]:
        if REQUIRE_MALWARE_SCAN:raise ValueError("A malware scanner is required but is not available; the upload was blocked")
        return {"status":"not-configured","clean":True}
    temp=QUARANTINE/f"scan-{uuid.uuid4().hex}-{Path(str(name or 'upload')).name}"
    temp.write_bytes(raw)
    try:
        command=malware_scan_command(temp)
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=MALWARE_SCAN_TIMEOUT_SECONDS)
        if result.returncode!=0:raise ValueError("The uploaded material failed the configured malware scan")
        return {"status":"clean","clean":True}
    except subprocess.TimeoutExpired as exc:
        raise ValueError("The configured malware scan timed out") from exc
    finally:
        try:temp.unlink(missing_ok=True)
        except OSError:pass

def cleanup_quarantine(max_age_seconds=24*60*60):
    cutoff=time.time()-max_age_seconds;removed=0
    for path in QUARANTINE.glob("*"):
        try:
            if path.is_file() and path.stat().st_mtime<cutoff:path.unlink();removed+=1
        except OSError:pass
    return removed

def evict_image_cache():
    files=[];total=0
    for path in IMAGE_CACHE.iterdir():
        try:
            if not path.is_file():continue
            stat=path.stat();files.append((stat.st_mtime,stat.st_size,path));total+=stat.st_size
        except OSError:continue
    if len(files)<=IMAGE_CACHE_MAX_FILES and total<=IMAGE_CACHE_MAX_BYTES:return 0
    removed=0
    for _,size,path in sorted(files):
        if len(files)-removed<=IMAGE_CACHE_MAX_FILES and total<=IMAGE_CACHE_MAX_BYTES:break
        try:path.unlink();removed+=1;total-=size
        except OSError:pass
    return removed

def safe_hex_color(value, fallback):
    value=str(value or "").strip()
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}",value) else fallback

def inspect_image_bytes(raw, mime=""):
    if not raw or not str(mime).startswith("image/"):return {"width":0,"height":0,"dominantColor":""}
    try:
        from PIL import Image,ImageOps
        Image.MAX_IMAGE_PIXELS=MAX_IMAGE_MEGAPIXELS*1_000_000
        with warnings.catch_warnings():
            warnings.simplefilter("error",Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image=ImageOps.exif_transpose(image)
                width,height=image.size
                if width<=0 or height<=0 or width>MAX_IMAGE_DIMENSION or height>MAX_IMAGE_DIMENSION or width*height>MAX_IMAGE_MEGAPIXELS*1_000_000:
                    raise ValueError(f"Image dimensions exceed the {MAX_IMAGE_DIMENSION}px / {MAX_IMAGE_MEGAPIXELS}MP safety limit")
                if getattr(image,"is_animated",False):image.seek(0)
                thumb=image.convert("RGB");thumb.thumbnail((48,48))
                colors=thumb.getcolors(maxcolors=48*48) or []
                if colors:
                    _,rgb=max(colors,key=lambda item:item[0]);dominant="#%02x%02x%02x"%rgb
                else:dominant=""
                return {"width":int(width),"height":int(height),"dominantColor":dominant}
    except (ValueError,Exception) as exc:
        if isinstance(exc,ValueError):raise
        raise ValueError("The uploaded image is invalid or unsafe to process") from exc

def available_social_image_format():
    try:
        from PIL import Image  # noqa: F401
        return "png"
    except Exception:return "svg"

def image_font(size, khmer=False, bold=False):
    try:
        from PIL import ImageFont
        candidates=[]
        if khmer:
            candidates += [
                "/usr/share/fonts/truetype/noto/NotoSansKhmer-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansKhmer-Bold.ttf" if bold else "/usr/share/fonts/opentype/noto/NotoSansKhmer-Regular.ttf",
                "C:/Windows/Fonts/KhmerUIb.ttf" if bold else "C:/Windows/Fonts/KhmerUI.ttf",
                "NotoSansKhmer-Bold.ttf" if bold else "NotoSansKhmer-Regular.ttf",
            ]
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ]
        for candidate in candidates:
            try:return ImageFont.truetype(candidate,max(8,int(size)))
            except Exception:pass
        return ImageFont.load_default()
    except Exception:return None

def text_is_khmer(value):
    return bool(re.search(r"[\u1780-\u17FF]",str(value or "")))

def fitted_text_lines(draw, text, font, max_width, max_lines=3):
    value=" ".join(str(text or "").split())
    if not value:return []
    units=value.split(" ") if " " in value else list(value)
    joiner=" " if " " in value else ""
    lines=[];current=""
    for unit in units:
        proposed=(current+joiner+unit).strip() if current else unit
        try:width=draw.textbbox((0,0),proposed,font=font)[2]
        except Exception:width=len(proposed)*12
        if current and width>max_width:
            lines.append(current);current=unit
            if len(lines)>=max_lines:break
        else:current=proposed
    if current and len(lines)<max_lines:lines.append(current)
    if len(lines)==max_lines and units:
        full=joiner.join(units)
        consumed=joiner.join(lines)
        if len(consumed)<len(full):lines[-1]=lines[-1].rstrip(" …")+"…"
    return lines

def resolve_document_photo_bytes(invite_id, photo_url):
    photo=str(photo_url or "").strip()
    if not photo:return None
    parsed=urlparse(photo)
    direct_path=unquote(parsed.path)
    if direct_path.startswith("/uploads/"):
        return read_stored_asset_bytes(Path(direct_path).name)
    with connect() as db:
        rows=db.execute("SELECT path FROM assets WHERE invitation_id=?",(invite_id,)).fetchall()
    for row in rows:
        candidate=asset_public_url(row["path"])
        if photo==candidate or (OBJECT_STORAGE_PUBLIC_BASE_URL and photo.rstrip("/")==candidate.rstrip("/")):
            return read_stored_asset_bytes(row["path"])
    return None

def dependency_status():
    status={"pillow":False,"qrcode":False}
    try:
        import PIL  # noqa: F401
        status["pillow"]=True
    except Exception:pass
    try:
        import qrcode  # noqa: F401
        status["qrcode"]=True
    except Exception:pass
    status["qrReady"]=bool(status["pillow"] and status["qrcode"])
    scanner=malware_scanner_status(probe=True)
    status["malwareScanner"]=scanner["mode"]
    status["malwareScanReady"]=bool(scanner["ready"])
    status["malwareScanRequired"]=bool(scanner["required"])
    return status

def social_cache_path(invitation_id, version, fmt):
    safe_fmt=fmt if fmt in {"og","square","story"} else "og"
    return SOCIAL_CACHE / f"{invitation_id}-v{int(version or 0)}-{safe_fmt}.png"

def invalidate_social_cache(invitation_id):
    for candidate in SOCIAL_CACHE.glob(f"{invitation_id}-v*-*.png"):
        try:candidate.unlink()
        except OSError:pass

def render_social_card_png_bytes(invite_id, access_mode, document, fmt="og"):
    try:
        from PIL import Image,ImageDraw,ImageOps
    except Exception:return None
    sizes={"og":(1200,630),"square":(1080,1080),"story":(1080,1920)};w,h=sizes.get(fmt,sizes["og"])
    private=access_mode=="password";d=document or {};f=d.get("fields",{}) if not private else {};social=d.get("socialCard",{}) if not private else {};palette=d.get("palette",{}) if not private else {}
    background=safe_hex_color(palette.get("background"),"#fff8f2");accent=safe_hex_color(d.get("accent"),"#9d4555");text_color="#ffffff" if social.get("textVariant")=="light" else safe_hex_color(palette.get("text"),"#342c26")
    canvas=Image.new("RGB",(w,h),background);draw=ImageDraw.Draw(canvas,"RGBA")
    photo=None if private else resolve_document_photo_bytes(invite_id,social.get("photo"))
    if photo:
        try:
            with Image.open(io.BytesIO(photo)) as source:
                source=ImageOps.exif_transpose(source).convert("RGB");canvas=ImageOps.fit(source,(w,h),method=Image.Resampling.LANCZOS,centering=(.5,.5));draw=ImageDraw.Draw(canvas,"RGBA")
            overlay=(0,0,0,118) if social.get("textVariant")=="light" else (255,248,242,170);draw.rectangle((0,0,w,h),fill=overlay)
        except Exception:pass
    else:
        if social.get("textVariant")=="light":canvas.paste(tuple(int(accent[i:i+2],16) for i in (1,3,5)),(0,0,w,h));draw=ImageDraw.Draw(canvas,"RGBA")
        draw.ellipse((w*.78,-h*.25,w*1.18,h*.38),fill=(*tuple(int(accent[i:i+2],16) for i in (1,3,5)),28));draw.ellipse((-w*.18,h*.65,w*.32,h*1.18),fill=(*tuple(int(accent[i:i+2],16) for i in (1,3,5)),20))
    margin=max(44,round(w*.045));radius=max(18,round(w*.02));draw.rounded_rectangle((margin,margin,w-margin,h-margin),radius=radius,outline=accent,width=max(3,round(w/320)))
    language=str(social.get("language") or d.get("languageMode") or "both");names_en=str(f.get("names") or "Invitation");names_km=str(f.get("namesKm") or "");venue_en=str(f.get("venue") or "");venue_km=str(f.get("venueKm") or "")
    if private:title_lines=["Private Invitation"];venue_text="";date_text=""
    elif language=="km":title_lines=[names_km or names_en];venue_text=venue_km or venue_en;date_text=str(f.get("date") or "")
    elif language=="both" and names_km and names_km!=names_en:title_lines=[names_en,names_km];venue_text=" · ".join(x for x in [venue_en,venue_km] if x);date_text=str(f.get("date") or "")
    else:title_lines=[names_en];venue_text=venue_en;date_text=str(f.get("date") or "")
    align=str(social.get("alignment") or "center");anchor_x=round(w*.11) if align=="left" else round(w*.89) if align=="right" else w//2;anchor="la" if align=="left" else "ra" if align=="right" else "ma"
    label="PRIVATE INVITATION" if private else ("សូមគោរពអញ្ជើញ" if language=="km" else "YOU ARE INVITED")
    label_font=image_font(w*.027,text_is_khmer(label),True);title_size=w*(.058 if len(title_lines)==1 else .047);title_y=round(h*.31 if h<1000 else h*.34)
    draw.text((anchor_x,round(h*.17)),label,font=label_font,fill=accent,anchor=anchor)
    monogram="" if private else str(social.get("monogram") or d.get("openingScene",{}).get("monogram") or "")[:8]
    if monogram:
        mono_font=image_font(w*.24,text_is_khmer(monogram),True);draw.text((w//2,h//2),monogram,font=mono_font,fill=(*tuple(int(accent[i:i+2],16) for i in (1,3,5)),24),anchor="mm")
    cursor=title_y
    for line in title_lines:
        font=image_font(title_size,text_is_khmer(line),True);wrapped=fitted_text_lines(draw,line,font,w*.76,2)
        for part in wrapped:
            draw.text((anchor_x,cursor),part,font=font,fill=text_color,anchor=anchor);cursor+=round(title_size*1.3)
        cursor+=round(title_size*.15)
    detail_font=image_font(w*.026,False,False);kh_detail=image_font(w*.026,True,False)
    detail_y=max(cursor+round(h*.04),round(h*.66 if h<1000 else h*.63))
    if date_text:draw.text((anchor_x,detail_y),date_text,font=detail_font,fill=text_color,anchor=anchor);detail_y+=round(w*.045)
    if venue_text:
        font=kh_detail if text_is_khmer(venue_text) else detail_font
        for part in fitted_text_lines(draw,venue_text,font,w*.72,3):draw.text((anchor_x,detail_y),part,font=font,fill=text_color,anchor=anchor);detail_y+=round(w*.037)
    out=io.BytesIO();canvas.save(out,"PNG",optimize=True);return out.getvalue()

def warm_social_card_cache(invitation_id, access_mode, version, document):
    def worker():
        for fmt in ("og","square","story"):
            try:
                payload=render_social_card_png_bytes(invitation_id,access_mode,document,fmt)
                if payload:
                    target=social_cache_path(invitation_id,version,fmt);tmp=target.with_suffix(".tmp");tmp.write_bytes(payload);tmp.replace(target)
            except Exception:pass
    threading.Thread(target=worker,daemon=True,name=f"social-card-{invitation_id}").start()

def make_qr_image(text, box_size=12, border=4):
    try:
        import qrcode
        qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=box_size,border=border)
        qr.add_data(str(text));qr.make(fit=True)
        return qr.make_image(fill_color="black",back_color="white").convert("RGB")
    except Exception:return None

_ALLOWED_RICH_TAGS = {"br", "b", "strong", "i", "em", "u", "s", "ul", "ol", "li", "span", "a"}
_DROP_RICH_TAGS = {"script", "style", "iframe", "object", "embed", "svg", "math", "template", "noscript"}
_ALLOWED_RICH_STYLES = {"color", "background-color", "font-weight", "font-style", "text-decoration", "text-align"}
_SAFE_STYLE_VALUE = re.compile(r"^[#(),.%\-\s\w]+$")

def _safe_rich_href(value):
    value = str(value or "").strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered.startswith(("http://", "https://", "mailto:", "tel:", "/", "#")):
        return value
    return ""

def _sanitize_rich_style(value):
    safe = []
    for declaration in str(value or "").split(";"):
        if ":" not in declaration:
            continue
        name, raw_value = declaration.split(":", 1)
        name = name.strip().lower()
        raw_value = raw_value.strip()
        if name not in _ALLOWED_RICH_STYLES or not raw_value or not _SAFE_STYLE_VALUE.fullmatch(raw_value):
            continue
        lowered = raw_value.lower().replace(" ", "")
        if "url(" in lowered or "expression(" in lowered or "javascript:" in lowered:
            continue
        safe.append(f"{name}:{raw_value}")
    return ";".join(safe)

class _RichTextSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.blocked_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _DROP_RICH_TAGS:
            self.blocked_depth += 1
            return
        if self.blocked_depth or tag not in _ALLOWED_RICH_TAGS:
            return
        safe_attrs = []
        attr_map = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag == "span":
            style = _sanitize_rich_style(attr_map.get("style", ""))
            if style:
                safe_attrs.append(("style", style))
        elif tag == "a":
            href = _safe_rich_href(attr_map.get("href", ""))
            if href:
                safe_attrs.append(("href", href))
            if attr_map.get("target") == "_blank":
                safe_attrs.extend((("target", "_blank"), ("rel", "noopener noreferrer")))
        rendered = "".join(f' {name}="{html.escape(value, quote=True)}"' for name, value in safe_attrs)
        self.parts.append(f"<{tag}{rendered}>")

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "br" and not self.blocked_depth:
            self.parts.append("<br>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _DROP_RICH_TAGS:
            if self.blocked_depth:
                self.blocked_depth -= 1
            return
        if not self.blocked_depth and tag in _ALLOWED_RICH_TAGS and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.blocked_depth:
            self.parts.append(html.escape(data, quote=False))

def sanitize_rich_text_html(value):
    parser = _RichTextSanitizer()
    parser.feed(str(value or ""))
    parser.close()
    return "".join(parser.parts)

def validate_document(document):
    if not isinstance(document, dict): raise ValueError("Invitation document must be an object")
    encoded = json.dumps(document, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 5_000_000: raise ValueError("Invitation document exceeds 5 MB")
    # V20 authoritative typography normalization runs before every consumer-specific check.
    # It validates semantic styles, links, overrides, stable font pairings and migrations.
    normalize_document_typography(document, strict=True)
    normalize_document_rich_text(document, strict=True)
    normalize_document_v32(document, strict=True, mutate=True)
    objects = document.get("objects", {})
    object_limit=5000 if int(document.get("schemaVersion") or 14)>=18 else 300
    if not isinstance(objects, dict) or len(objects) > object_limit: raise ValueError("Invitation contains too many design objects")
    allowed_animations = {"fade-up", "soft-zoom", "slide-left", "blur-in", "bounce-in", "flip-in", "float", "none"}
    dimension_pattern = re.compile(r"^-?\d+(?:\.\d+)?(?:%|px)?$")
    for object_id, obj in objects.items():
        if not isinstance(object_id, str) or len(object_id) > 120 or not isinstance(obj, dict): raise ValueError("Invalid design object")
        if obj.get("type") not in (None, "text", "image", "shape", "decoration"): raise ValueError("Unsupported design object type")
        raw_html = str(obj.get("html", "") or "")
        if len(raw_html.encode("utf-8")) > 200_000: raise ValueError("Design object text is too large")
        obj["html"] = sanitize_rich_text_html(raw_html)
        for key in ("left", "top", "width", "height"):
            value = obj.get(key)
            if value not in (None, "") and (not isinstance(value, str) or len(value) > 40 or not dimension_pattern.fullmatch(value.strip())):
                raise ValueError("Invalid design object dimensions")
        animation = obj.get("animation")
        if animation not in (None, "") and animation not in allowed_animations: raise ValueError("Unsupported object animation")
        duration = obj.get("duration")
        if duration not in (None, ""):
            try: duration_value = float(duration)
            except (TypeError, ValueError): raise ValueError("Invalid object animation duration")
            if not 100 <= duration_value <= 10000: raise ValueError("Invalid object animation duration")
        try: rotation = float(obj.get("rotation", 0))
        except (TypeError, ValueError): raise ValueError("Invalid object rotation")
        if not -360 <= rotation <= 360: raise ValueError("Invalid object rotation")
        for key in ("imagePositionX", "imagePositionY"):
            try: position = float(obj.get(key, 50))
            except (TypeError, ValueError): raise ValueError("Invalid image focal position")
            if not 0 <= position <= 100: raise ValueError("Invalid image focal position")
        # V19.1 typography is a server-enforced contract. Stored fonts are
        # stable registry IDs only; known V19 stacks migrate to those IDs.
        obj["font"] = normalize_font_id(obj.get("font", "noto-serif"), strict=True)
        font_size = finite_number(obj.get("fontSize", 32), 32, 8, 200, strict=True)
        obj["fontSize"] = font_size
        text_auto_fit = obj.get("textAutoFit", "none")
        if text_auto_fit not in {"none", "fit"}: raise ValueError("Invalid text auto-fit mode")
        obj["textAutoFit"] = text_auto_fit
        text_auto_fit_max = finite_number(obj.get("textAutoFitMax", font_size), font_size, 8, 200, strict=True)
        text_min_font_size = finite_number(obj.get("textMinFontSize", 10), 10, 8, 72, strict=True)
        if text_min_font_size > text_auto_fit_max: raise ValueError("Minimum text size exceeds auto-fit maximum")
        obj["textAutoFitMax"] = text_auto_fit_max
        obj["textMinFontSize"] = text_min_font_size
        text_wrap = obj.get("textWrap", "normal")
        if text_wrap not in {"normal", "balance", "pretty"}: raise ValueError("Invalid text wrapping mode")
        obj["textWrap"] = text_wrap
        raw_columns = finite_number(obj.get("textColumns", 1), 1, 1, 3, strict=True)
        if raw_columns != int(raw_columns): raise ValueError("Text columns must be an integer")
        obj["textColumns"] = int(raw_columns)
        obj["textColumnGap"] = finite_number(obj.get("textColumnGap", 24), 24, 0, 64, strict=True)
        text_align = obj.get("textAlign", "center")
        if text_align not in {"left", "center", "right", "justify"}: raise ValueError("Invalid text alignment")
        obj["textAlign"] = text_align
        if obj.get("textVerticalAlign", "middle") not in {"top", "middle", "bottom"}: raise ValueError("Invalid vertical text alignment")
        try: text_padding = float(obj.get("textPadding", 8) if obj.get("textPadding", 8) is not None else 8)
        except (TypeError, ValueError): raise ValueError("Invalid text padding")
        if not 0 <= text_padding <= 64: raise ValueError("Invalid text padding")
        if obj.get("fontWeight", "400") not in {"400", "700", 400, 700}: raise ValueError("Invalid font weight")
        if obj.get("fontStyle", "normal") not in {"normal", "italic"}: raise ValueError("Invalid font style")
        try: letter_spacing = float(obj.get("letterSpacing", 0) or 0); line_height = float(obj.get("lineHeight", 1.35) or 1.35)
        except (TypeError, ValueError): raise ValueError("Invalid text spacing")
        if not -2 <= letter_spacing <= 20 or not 0.8 <= line_height <= 3: raise ValueError("Invalid text spacing")
        if obj.get("shapeKind", "rectangle") not in {"rectangle", "circle", "line"}: raise ValueError("Invalid shape kind")
        try: opacity = float(obj.get("opacity", 1))
        except (TypeError, ValueError): raise ValueError("Invalid object opacity")
        if not 0.05 <= opacity <= 1: raise ValueError("Invalid object opacity")
        for key, maximum in (("borderWidth", 20), ("borderRadius", 300), ("shadowBlur", 120)):
            try: style_number = float(obj.get(key, 0) or 0)
            except (TypeError, ValueError): raise ValueError("Invalid object appearance value")
            if not 0 <= style_number <= maximum: raise ValueError("Invalid object appearance value")
        if obj.get("backgroundEnabled", False) not in (True, False): raise ValueError("Invalid object background setting")
        try: background_opacity = float(obj.get("backgroundOpacity", 100) if obj.get("backgroundOpacity", 100) is not None else 100)
        except (TypeError, ValueError): raise ValueError("Invalid object background opacity")
        if not 0 <= background_opacity <= 100: raise ValueError("Invalid object background opacity")
        if obj.get("blendMode", "normal") not in {"normal","multiply","screen","overlay","soft-light","darken","lighten"}: raise ValueError("Invalid object blend mode")
        if obj.get("fillMode", "solid") not in {"solid","gradient"}: raise ValueError("Invalid object fill mode")
        try: gradient_angle=float(obj.get("gradientAngle",135) or 135); text_gradient_angle=float(obj.get("textGradientAngle",90) or 90)
        except (TypeError,ValueError): raise ValueError("Invalid object gradient angle")
        if not 0 <= gradient_angle <= 360 or not 0 <= text_gradient_angle <= 360: raise ValueError("Invalid object gradient angle")
        if obj.get("textGradientEnabled", False) not in (True, False): raise ValueError("Invalid text gradient setting")
        try:
            text_stroke=float(obj.get("textStrokeWidth",0) or 0); text_shadow=float(obj.get("textShadowBlur",0) or 0); animation_delay=float(obj.get("animationDelay",0) or 0)
        except (TypeError,ValueError): raise ValueError("Invalid advanced object style")
        if not 0 <= text_stroke <= 8 or not 0 <= text_shadow <= 40 or not 0 <= animation_delay <= 5000: raise ValueError("Invalid advanced object style")
        if obj.get("textTransform", "none") not in {"none","uppercase","lowercase","capitalize"}: raise ValueError("Invalid text transform")
        color_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for key in ("borderColor", "shadowColor", "fillColor", "backgroundColor", "gradientStart", "gradientEnd", "textGradientStart", "textGradientEnd", "textStrokeColor", "textShadowColor"):
            value = obj.get(key)
            if value not in (None, "") and (not isinstance(value, str) or not color_pattern.fullmatch(value)): raise ValueError("Invalid object color")
        if len(str(obj.get("groupId", ""))) > 120: raise ValueError("Invalid object group")
        if obj.get("visible", True) not in (True, False): raise ValueError("Invalid object visibility")
        if len(str(obj.get("layerName", ""))) > 80: raise ValueError("Invalid layer name")
        if obj.get("imageMask", "none") not in {"none", "circle", "arch", "diamond", "hexagon", "blob"}: raise ValueError("Invalid image mask")
        if obj.get("imageFrame", "none") not in {"none", "white", "gold", "dark"}: raise ValueError("Invalid image frame")
        image_filter_ranges = {
            "imageBrightness": (20, 200, 100),
            "imageContrast": (20, 200, 100),
            "imageSaturation": (0, 250, 100),
            "imageGrayscale": (0, 100, 0),
            "imageSepia": (0, 100, 0),
            "imageBlur": (0, 20, 0),
            "imageHue": (-180, 180, 0),
            "imageVibrance": (-100, 100, 0),
            "imageTemperature": (-100, 100, 0),
            "imageGamma": (0.25, 3, 1),
            "imageCurveShadows": (-100, 100, 0),
            "imageCurveHighlights": (-100, 100, 0),
            "imageSharpen": (0, 100, 0),
            "imageLevelsBlack": (0, 80, 0),
            "imageLevelsWhite": (20, 100, 100),
            "imagePerspectiveX": (-60, 60, 0),
            "imagePerspectiveY": (-60, 60, 0),
            "imageWarpX": (-30, 30, 0),
            "imageWarpY": (-30, 30, 0),
            "imageMaskFeather": (0, 50, 0),
            "imageGradientMask": (0, 100, 0),
        }
        for key, (minimum, maximum, default) in image_filter_ranges.items():
            try: value = float(obj.get(key, default) if obj.get(key, default) is not None else default)
            except (TypeError, ValueError): raise ValueError("Invalid image filter value")
            if not minimum <= value <= maximum: raise ValueError("Invalid image filter value")
        for key in ("imageFlipX", "imageFlipY"):
            if obj.get(key, False) not in (True, False): raise ValueError("Invalid image flip setting")
    section_layouts = document.get("sectionLayouts", {})
    if section_layouts is not None:
        if not isinstance(section_layouts, dict) or len(section_layouts) > 10: raise ValueError("Invalid section layouts")
        allowed_layouts = {
            "countdown": {"cards", "minimal", "pill"},
            "schedule": {"timeline", "cards", "minimal"},
            "custom": {"cards", "editorial", "alternating"},
            "venue": {"cards", "stacked", "split"},
        }
        for name, value in section_layouts.items():
            if name not in allowed_layouts or value not in allowed_layouts[name]: raise ValueError("Unsupported section layout")
    section_styles = document.get("sectionStyles", {})
    if section_styles is not None:
        if not isinstance(section_styles, dict) or len(section_styles) > 20: raise ValueError("Invalid section styles")
        allowed_style_sections = {"gallery", "video", "countdown", "schedule", "custom", "venue", "contact", "rsvp", "wishes"}
        color_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for name, style in section_styles.items():
            if name not in allowed_style_sections or not isinstance(style, dict): raise ValueError("Invalid section style")
            for flag in ("backgroundEnabled", "textColorEnabled", "backgroundImageEnabled"):
                if flag in style and not isinstance(style[flag], bool): raise ValueError("Invalid section style toggle")
            for color_key in ("background", "textColor"):
                value = style.get(color_key)
                if value not in (None, "") and (not isinstance(value, str) or not color_pattern.fullmatch(value)): raise ValueError("Invalid section style color")
            try: radius = float(style.get("radius", 0) or 0)
            except (TypeError, ValueError): raise ValueError("Invalid section style radius")
            if not 0 <= radius <= 60: raise ValueError("Invalid section style radius")
            image = str(style.get("backgroundImage", "") or "")
            if len(image) > 4_000_000: raise ValueError("Section background image is too large")
            if image and not (re.match(r"^https?://", image, re.I) or image.startswith("/data/uploads/") or re.match(r"^data:image/(?:jpeg|png|webp|gif);base64,", image, re.I)): raise ValueError("Invalid section background image")
            if style.get("backgroundSize", "cover") not in {"cover", "contain"}: raise ValueError("Invalid section background size")
            try: overlay = float(style.get("backgroundOverlay", 0) or 0)
            except (TypeError, ValueError): raise ValueError("Invalid section background overlay")
            if not 0 <= overlay <= 80: raise ValueError("Invalid section background overlay")
    palette_preset = document.get("palettePreset", "template")
    if palette_preset not in {"template", "rose", "gold", "emerald", "midnight", "ivory-navy", "custom"}: raise ValueError("Invalid palette preset")
    palette = document.get("palette", {})
    if palette is not None:
        if not isinstance(palette, dict): raise ValueError("Invalid palette")
        color_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
        for key in ("background", "surface", "text", "heading"):
            value = palette.get(key)
            if value not in (None, "") and (not isinstance(value, str) or not color_pattern.fullmatch(value)): raise ValueError("Invalid palette color")
    background_effects = document.get("backgroundEffects", {}) or {}
    if not isinstance(background_effects, dict): raise ValueError("Invalid invitation background effects")
    if background_effects.get("mode", "none") not in {"none", "solid", "gradient"}: raise ValueError("Invalid invitation background mode")
    if background_effects.get("texture", "none") not in {"none", "paper", "dots", "grid", "soft-grain"}: raise ValueError("Invalid invitation background texture")
    for key in ("start", "end"):
        value = background_effects.get(key)
        if value not in (None, "") and (not isinstance(value, str) or not color_pattern.fullmatch(value)): raise ValueError("Invalid invitation background color")
    try:
        bg_angle=float(background_effects.get("angle",135) or 135); texture_opacity=float(background_effects.get("textureOpacity",18) if background_effects.get("textureOpacity",18) is not None else 18)
    except (TypeError,ValueError): raise ValueError("Invalid invitation background effect")
    if not 0 <= bg_angle <= 360 or not 0 <= texture_opacity <= 60: raise ValueError("Invalid invitation background effect")
    section_animations = document.get("sectionAnimations", {})
    if section_animations is not None:
        if not isinstance(section_animations, dict) or len(section_animations) > 20: raise ValueError("Invalid section animations")
        allowed_animation_sections = {"hero", "gallery", "video", "countdown", "schedule", "custom", "venue", "contact", "rsvp", "wishes"}
        for name, settings in section_animations.items():
            if name not in allowed_animation_sections or not isinstance(settings, dict): raise ValueError("Invalid section animation")
            if settings.get("preset", "fade-up") not in allowed_animations: raise ValueError("Unsupported section animation")
            try: section_duration = float(settings.get("duration", 900))
            except (TypeError, ValueError): raise ValueError("Invalid section animation duration")
            if not 100 <= section_duration <= 10000: raise ValueError("Invalid section animation duration")
    design_pages = document.get("designPages", [])
    if not isinstance(design_pages, list) or len(design_pages) > 30: raise ValueError("Invalid visual page list")
    page_ids = set()
    color_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    for page in design_pages:
        if not isinstance(page, dict): raise ValueError("Invalid visual page")
        page_id = str(page.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", page_id) or page_id in page_ids: raise ValueError("Invalid visual page id")
        page_ids.add(page_id)
        if len(str(page.get("name", ""))) > 120: raise ValueError("Visual page name is too long")
        if "enabled" in page and not isinstance(page.get("enabled"), bool): raise ValueError("Invalid visual page visibility")
        background = page.get("background", "#fffaf6")
        if not isinstance(background, str) or not color_pattern.fullmatch(background): raise ValueError("Invalid visual page background")
        image = str(page.get("backgroundImage", "") or "")
        if len(image) > 4_000_000: raise ValueError("Visual page background image is too large")
        if image and not (re.match(r"^https?://", image, re.I) or image.startswith("/data/uploads/") or re.match(r"^data:image/(?:jpeg|png|webp|gif);base64,", image, re.I)): raise ValueError("Invalid visual page background image")
        if page.get("backgroundSize", "cover") not in {"cover", "contain"}: raise ValueError("Invalid visual page background size")
        try: overlay = float(page.get("backgroundOverlay", 0) or 0)
        except (TypeError, ValueError): raise ValueError("Invalid visual page overlay")
        if not 0 <= overlay <= 80: raise ValueError("Invalid visual page overlay")
        animation = page.get("animation", {}) or {}
        if not isinstance(animation, dict) or animation.get("preset", "fade-up") not in allowed_animations: raise ValueError("Invalid visual page animation")
        try: page_duration = float(animation.get("duration", 900))
        except (TypeError, ValueError): raise ValueError("Invalid visual page animation duration")
        if not 100 <= page_duration <= 10000: raise ValueError("Invalid visual page animation duration")
        page_objects = page.get("objects", {})
        if not isinstance(page_objects, dict) or len(page_objects) > object_limit: raise ValueError("Visual page contains too many design objects")
        if page.get("useMasterBackground", False) not in (True, False): raise ValueError("Invalid page master background setting")
        transition=page.get("transition", {}) or {}
        if not isinstance(transition, dict) or transition.get("preset", "soft") not in {"none","soft","overlap","sweep"}: raise ValueError("Invalid page transition")
        try: transition_duration=float(transition.get("duration",600))
        except (TypeError,ValueError): raise ValueError("Invalid page transition duration")
        if not 200 <= transition_duration <= 2000: raise ValueError("Invalid page transition duration")
        validate_document({"objects": page_objects, "typography": document["typography"]})
    master=document.get("masterPageStyle", {}) or {}
    if not isinstance(master,dict): raise ValueError("Invalid master page style")
    if master.get("enabled",False) not in (True,False): raise ValueError("Invalid master page style")
    color=master.get("background", "#fffaf6")
    if color and not re.fullmatch(r"#[0-9a-fA-F]{6}",str(color)): raise ValueError("Invalid master page background")
    image=str(master.get("backgroundImage","") or "")
    if image and not (re.match(r"^https?://",image,re.I) or image.startswith("/uploads/") or image.startswith("/data/uploads/") or re.match(r"^data:image/(?:jpeg|png|webp|gif);base64,",image,re.I)): raise ValueError("Invalid master page background image")
    if master.get("backgroundSize","cover") not in {"cover","contain"}: raise ValueError("Invalid master page background size")
    try: master_overlay=float(master.get("backgroundOverlay",0) or 0)
    except (TypeError,ValueError): raise ValueError("Invalid master page overlay")
    if not 0 <= master_overlay <= 80: raise ValueError("Invalid master page overlay")
    order = document.get("sectionOrder", [])
    allowed_sections = {"gallery", "video", "countdown", "events", "schedule", "custom", "guest-info", "venue", "contact", "rsvp", "wishes"}
    if order is not None:
        if not isinstance(order, list) or len(order) > 80: raise ValueError("Invalid section order")
        for item in order:
            if not isinstance(item, str): raise ValueError("Section order contains an unsupported section")
            if item in allowed_sections: continue
            if item.startswith("page:") and item[5:] in page_ids: continue
            raise ValueError("Section order contains an unsupported section")
        if len(order) != len(set(order)): raise ValueError("Section order contains duplicates")
    rsvp_fields=document.get("rsvpFields", [])
    if not isinstance(rsvp_fields,list) or len(rsvp_fields)>20:raise ValueError("Invalid RSVP custom fields")
    field_ids=set()
    for field in rsvp_fields:
        if not isinstance(field,dict):raise ValueError("Invalid RSVP custom field")
        field_id=str(field.get("id",""))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",field_id) or field_id in field_ids:raise ValueError("Invalid RSVP custom field id")
        field_ids.add(field_id)
        if field.get("type","text") not in {"text","textarea","select","number"}:raise ValueError("Unsupported RSVP custom field type")
        if not isinstance(field.get("required",False),bool):raise ValueError("Invalid RSVP custom field requirement")
        for key in ("label","labelKm"):
            if len(str(field.get(key,"")))>200:raise ValueError("RSVP custom field label is too long")
        options=field.get("options",[])
        if not isinstance(options,list) or len(options)>30 or any(len(str(x))>120 for x in options):raise ValueError("Invalid RSVP custom field options")

    schedule = document.get("schedule", [])
    if not isinstance(schedule, list) or len(schedule) > 100: raise ValueError("Invalid schedule")
    venues = document.get("venues", [])
    if not isinstance(venues, list) or len(venues) > 50: raise ValueError("Invalid venue list")
    blocks = document.get("customBlocks", [])
    if not isinstance(blocks, list) or len(blocks) > 50: raise ValueError("Invalid custom section list")
    for block in blocks:
        if not isinstance(block, dict): raise ValueError("Invalid custom section")
        for key in ("heading", "headingKm", "body", "bodyKm"):
            if len(str(block.get(key, ""))) > (5000 if key.startswith("body") else 300): raise ValueError("Custom section text is too long")
    video=document.get("video")
    if video is not None:
        if not isinstance(video,dict): raise ValueError("Invalid featured video")
        video_url=str(video.get("url","") or "")
        if len(video_url)>7_000_000: raise ValueError("Featured video reference is too large")
        if video_url and not (re.match(r"^https?://",video_url,re.I) or video_url.startswith("/uploads/") or video_url.startswith("/data/uploads/") or re.match(r"^data:video/(?:mp4|webm);base64,",video_url,re.I)): raise ValueError("Invalid featured video URL")
        if video.get("mime") and video.get("mime") not in {"video/mp4","video/webm"}: raise ValueError("Invalid featured video type")
    return document

_SQLITE_SCHEMA_READY=False
_SQLITE_SCHEMA_LOCK=threading.Lock()

@contextmanager
def connect_sqlite():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA foreign_keys=ON")
    try:
        global _SQLITE_SCHEMA_READY
        if not _SQLITE_SCHEMA_READY:
            with _SQLITE_SCHEMA_LOCK:
                if not _SQLITE_SCHEMA_READY:
                    db.executescript("""
                    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, salt TEXT NOT NULL, password_algo TEXT NOT NULL DEFAULT 'pbkdf2-sha256-v1', created_at INTEGER NOT NULL, role TEXT NOT NULL DEFAULT 'customer', email_verified INTEGER NOT NULL DEFAULT 0, plan TEXT NOT NULL DEFAULT 'free', upload_enabled INTEGER NOT NULL DEFAULT 1, mfa_secret TEXT, mfa_enabled INTEGER NOT NULL DEFAULT 0, deleted_at INTEGER, deletion_scheduled_at INTEGER, privacy_json TEXT NOT NULL DEFAULT '{}', studio_name TEXT NOT NULL DEFAULT '', white_label_json TEXT NOT NULL DEFAULT '{}');
                    CREATE TABLE IF NOT EXISTS billing_orders(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', provider TEXT NOT NULL DEFAULT '', provider_session_id TEXT NOT NULL DEFAULT '', amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, paid_at INTEGER);
                    CREATE INDEX IF NOT EXISTS idx_billing_orders_user_time ON billing_orders(user_id,created_at DESC);
                    CREATE TABLE IF NOT EXISTS billing_events(id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload_hash TEXT NOT NULL, received_at INTEGER NOT NULL, processed_at INTEGER);
                    CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, id TEXT NOT NULL DEFAULT '', user_id TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL, user_agent TEXT NOT NULL DEFAULT '', ip_address TEXT NOT NULL DEFAULT '', last_seen_at INTEGER NOT NULL DEFAULT 0, device_name TEXT NOT NULL DEFAULT '', csrf_hash TEXT NOT NULL DEFAULT '');
                    CREATE TABLE IF NOT EXISTS invitations(id TEXT PRIMARY KEY, slug TEXT UNIQUE NOT NULL, draft_json TEXT NOT NULL, updated_at INTEGER NOT NULL, owner_id TEXT, archived INTEGER NOT NULL DEFAULT 0, views INTEGER NOT NULL DEFAULT 0, last_client_id TEXT, last_mutation_id TEXT, deleted_at INTEGER, purge_at INTEGER, custom_domain TEXT, publish_at INTEGER, unpublish_at INTEGER, expires_at INTEGER, gallery_access_password_hash TEXT, gallery_access_password_salt TEXT);
                    CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, version INTEGER NOT NULL, document_json TEXT NOT NULL, published_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS rsvps(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, guest_id TEXT, name TEXT NOT NULL, normalized_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, guest_count INTEGER NOT NULL, note TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL DEFAULT 0, answers_json TEXT NOT NULL DEFAULT '{}');
                    CREATE TABLE IF NOT EXISTS stored_objects(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, path TEXT UNIQUE NOT NULL, storage_key TEXT NOT NULL DEFAULT '', sha256 TEXT NOT NULL DEFAULT '', mime TEXT NOT NULL, size INTEGER NOT NULL, width INTEGER NOT NULL DEFAULT 0, height INTEGER NOT NULL DEFAULT 0, dominant_color TEXT NOT NULL DEFAULT '', processing_state TEXT NOT NULL DEFAULT 'ready', quarantine_state TEXT NOT NULL DEFAULT 'released', scan_status TEXT NOT NULL DEFAULT 'not-configured', ref_count INTEGER NOT NULL DEFAULT 0, deleted_at INTEGER, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_stored_objects_owner_hash ON stored_objects(owner_id,sha256,size,mime);
                    CREATE INDEX IF NOT EXISTS idx_stored_objects_path ON stored_objects(path);
                    CREATE TABLE IF NOT EXISTS background_jobs(id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0, available_at INTEGER NOT NULL, locked_at INTEGER, last_error TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_background_jobs_queue ON background_jobs(state,available_at,created_at);
                    CREATE TABLE IF NOT EXISTS bandwidth_events(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, bytes INTEGER NOT NULL, created_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_bandwidth_events_owner_time ON bandwidth_events(owner_id,created_at);
                    CREATE TABLE IF NOT EXISTS backup_runs(id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL, detail_json TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL, completed_at INTEGER, owner_id TEXT NOT NULL DEFAULT '', initiated_by TEXT NOT NULL DEFAULT '', archive_name TEXT NOT NULL DEFAULT '', size_bytes INTEGER NOT NULL DEFAULT 0, error_text TEXT NOT NULL DEFAULT '');
                    CREATE TABLE IF NOT EXISTS studio_backup_policies(owner_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0, interval_hours INTEGER NOT NULL DEFAULT 24, retention_count INTEGER NOT NULL DEFAULT 7, include_media INTEGER NOT NULL DEFAULT 1, updated_by TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL DEFAULT 0, last_run_at INTEGER, next_run_at INTEGER);
                    CREATE TABLE IF NOT EXISTS studio_bulk_jobs(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'completed', selection_json TEXT NOT NULL DEFAULT '{}', result_json TEXT NOT NULL DEFAULT '{}', created_by TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, completed_at INTEGER);
                    CREATE INDEX IF NOT EXISTS idx_studio_bulk_jobs_owner_time ON studio_bulk_jobs(owner_id,created_at DESC);
                    CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, created_at INTEGER NOT NULL, folder TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]', favorite INTEGER NOT NULL DEFAULT 0, sha256 TEXT NOT NULL DEFAULT '', width INTEGER NOT NULL DEFAULT 0, height INTEGER NOT NULL DEFAULT 0, dominant_color TEXT NOT NULL DEFAULT '', object_id TEXT, processing_state TEXT NOT NULL DEFAULT 'ready');
                    CREATE TABLE IF NOT EXISTS upload_sessions(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, owner_id TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL, expected_size INTEGER NOT NULL, received_size INTEGER NOT NULL DEFAULT 0, temp_path TEXT NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL); 
                    CREATE INDEX IF NOT EXISTS idx_upload_sessions_expiry ON upload_sessions(expires_at);
                    CREATE TABLE IF NOT EXISTS material_folders(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, parent_id TEXT, name TEXT NOT NULL, relative_key TEXT NOT NULL, created_by TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, UNIQUE(invitation_id,relative_key));
                    CREATE INDEX IF NOT EXISTS idx_material_folders_invitation ON material_folders(invitation_id,relative_key);
                    CREATE TABLE IF NOT EXISTS material_import_jobs(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, owner_id TEXT NOT NULL, source_type TEXT NOT NULL, root_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'queued', total_files INTEGER NOT NULL DEFAULT 0, processed_files INTEGER NOT NULL DEFAULT 0, failed_files INTEGER NOT NULL DEFAULT 0, total_bytes INTEGER NOT NULL DEFAULT 0, processed_bytes INTEGER NOT NULL DEFAULT 0, failures_json TEXT NOT NULL DEFAULT '[]', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, cancelled_at INTEGER);
                    CREATE INDEX IF NOT EXISTS idx_material_import_jobs_invitation ON material_import_jobs(invitation_id,created_at DESC);
                    CREATE TABLE IF NOT EXISTS guests(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL, phone TEXT, email TEXT NOT NULL DEFAULT '', group_name TEXT NOT NULL DEFAULT '', household_id TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]', table_name TEXT NOT NULL DEFAULT '', seat_label TEXT NOT NULL DEFAULT '', token TEXT UNIQUE NOT NULL, token_hash TEXT, token_salt TEXT NOT NULL DEFAULT '', token_version INTEGER NOT NULL DEFAULT 1, token_expires_at INTEGER, token_revoked_at INTEGER, created_at INTEGER NOT NULL, checked_in INTEGER NOT NULL DEFAULT 0, checked_in_at INTEGER, delivery_status TEXT NOT NULL DEFAULT 'not-sent', opened_at INTEGER);
                    CREATE TABLE IF NOT EXISTS user_templates(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, document_json TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, description TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]', favorite INTEGER NOT NULL DEFAULT 0, current_version INTEGER NOT NULL DEFAULT 1, thumbnail_json TEXT NOT NULL DEFAULT '{}', visibility TEXT NOT NULL DEFAULT 'private', published_at INTEGER, marketplace_status TEXT NOT NULL DEFAULT 'draft', license_type TEXT NOT NULL DEFAULT 'personal');
                    CREATE TABLE IF NOT EXISTS template_versions(id TEXT PRIMARY KEY, template_id TEXT NOT NULL, version INTEGER NOT NULL, document_json TEXT NOT NULL, created_at INTEGER NOT NULL);
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_template_versions_unique ON template_versions(template_id,version);
                    CREATE TABLE IF NOT EXISTS user_page_templates(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'General', page_json TEXT NOT NULL, favorite INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS view_events(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, viewed_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_view_events_invitation ON view_events(invitation_id,viewed_at);
                    CREATE TABLE IF NOT EXISTS access_tokens(token_hash TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS gallery_access_tokens(token_hash TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_gallery_access_tokens_invite ON gallery_access_tokens(invitation_id,expires_at);
                    CREATE TABLE IF NOT EXISTS user_components(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'General', payload_json TEXT NOT NULL, favorite INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS studio_resources(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'General', payload_json TEXT NOT NULL, governance_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'draft', version INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS studio_governance(owner_id TEXT PRIMARY KEY, policy_json TEXT NOT NULL DEFAULT '{}', updated_at INTEGER NOT NULL DEFAULT 0);
                    CREATE TABLE IF NOT EXISTS studio_releases(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft', manifest_json TEXT NOT NULL DEFAULT '[]', version INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, activated_at INTEGER);
                    CREATE INDEX IF NOT EXISTS idx_studio_releases_owner_status ON studio_releases(owner_id,status,updated_at DESC);
                    CREATE TABLE IF NOT EXISTS invitation_studio_release_pins(invitation_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, release_id TEXT NOT NULL, release_version INTEGER NOT NULL DEFAULT 1, pinned_by TEXT NOT NULL DEFAULT '', pinned_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_studio_release_pins_owner ON invitation_studio_release_pins(owner_id,release_id,updated_at DESC);
                    CREATE TABLE IF NOT EXISTS guest_messages(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, name TEXT NOT NULL, message TEXT NOT NULL, created_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS message_campaigns(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, owner_id TEXT NOT NULL, name TEXT NOT NULL, channel TEXT NOT NULL, message TEXT NOT NULL, segment_json TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL DEFAULT 'draft', scheduled_at INTEGER, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS message_deliveries(id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, guest_id TEXT NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL, provider_id TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_message_deliveries_campaign ON message_deliveries(campaign_id,status);
                    CREATE TABLE IF NOT EXISTS invitation_comments(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL, object_id TEXT NOT NULL DEFAULT '', page_id TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', anchor_x REAL NOT NULL DEFAULT -1, anchor_y REAL NOT NULL DEFAULT -1, body TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_invitation_comments_invite ON invitation_comments(invitation_id,resolved,created_at);
                    CREATE TABLE IF NOT EXISTS approval_requests(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, requested_by TEXT NOT NULL, requested_from TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', note TEXT NOT NULL DEFAULT '', document_revision INTEGER NOT NULL DEFAULT 0, document_fingerprint TEXT NOT NULL DEFAULT '', summary_json TEXT NOT NULL DEFAULT '{}', decided_by TEXT NOT NULL DEFAULT '', decided_at INTEGER, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS invitation_review_policies(invitation_id TEXT PRIMARY KEY, approval_gate INTEGER NOT NULL DEFAULT 0, unresolved_comments_gate INTEGER NOT NULL DEFAULT 0, min_approvals INTEGER NOT NULL DEFAULT 1, updated_by TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL DEFAULT 0);
                    CREATE TABLE IF NOT EXISTS review_notifications(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, user_id TEXT NOT NULL, actor_id TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, target_id TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '', read_at INTEGER, created_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_review_notifications_user ON review_notifications(user_id,read_at,created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_review_notifications_invite ON review_notifications(invitation_id,user_id,created_at DESC);
                    CREATE TABLE IF NOT EXISTS review_tasks(comment_id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, assignee_id TEXT NOT NULL DEFAULT '', due_date TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL DEFAULT 'normal', status TEXT NOT NULL DEFAULT 'open', updated_by TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL DEFAULT 0);
                    CREATE INDEX IF NOT EXISTS idx_review_tasks_invite ON review_tasks(invitation_id,status,due_date);
                    CREATE INDEX IF NOT EXISTS idx_review_tasks_assignee ON review_tasks(assignee_id,status,due_date);
                    CREATE TABLE IF NOT EXISTS auth_tokens(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS audit_events(id TEXT PRIMARY KEY, user_id TEXT, action TEXT NOT NULL, target_type TEXT NOT NULL DEFAULT '', target_id TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}', ip_address TEXT NOT NULL DEFAULT '', previous_hash TEXT NOT NULL DEFAULT '', event_hash TEXT NOT NULL, created_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id,created_at DESC);
                    CREATE TABLE IF NOT EXISTS auth_challenges(id TEXT PRIMARY KEY, user_id TEXT, kind TEXT NOT NULL, challenge TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', expires_at INTEGER NOT NULL, used_at INTEGER);
                    CREATE INDEX IF NOT EXISTS idx_auth_challenges_expiry ON auth_challenges(expires_at);
                    CREATE TABLE IF NOT EXISTS passkeys(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, credential_id TEXT UNIQUE NOT NULL, public_key TEXT NOT NULL, sign_count INTEGER NOT NULL DEFAULT 0, transports_json TEXT NOT NULL DEFAULT '[]', name TEXT NOT NULL DEFAULT 'Passkey', created_at INTEGER NOT NULL, last_used_at INTEGER);
                    CREATE INDEX IF NOT EXISTS idx_passkeys_user ON passkeys(user_id,created_at DESC);
                    CREATE TABLE IF NOT EXISTS deleted_items(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL, item_id TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', deleted_at INTEGER NOT NULL, purge_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS idx_deleted_items_owner ON deleted_items(owner_id,deleted_at DESC);
                    CREATE TABLE IF NOT EXISTS invitation_collaborators(invitation_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'viewer', created_at INTEGER NOT NULL, PRIMARY KEY(invitation_id,user_id));
                    CREATE INDEX IF NOT EXISTS idx_invitation_collaborators_user ON invitation_collaborators(user_id,created_at);
                    CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_kind ON auth_tokens(user_id,kind,expires_at);
                    CREATE INDEX IF NOT EXISTS idx_user_components_owner_kind ON user_components(owner_id,kind,updated_at);
                    CREATE INDEX IF NOT EXISTS idx_studio_resources_owner_kind ON studio_resources(owner_id,kind,status,updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_invitations_owner ON invitations(owner_id,updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_publications_invitation ON publications(invitation_id,published_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_rsvps_invitation ON rsvps(invitation_id,created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_assets_invitation ON assets(invitation_id,created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_guests_invitation ON guests(invitation_id,created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_templates_owner ON user_templates(owner_id,updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_page_templates_owner ON user_page_templates(owner_id,updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                    CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
                    CREATE INDEX IF NOT EXISTS idx_access_tokens_invitation ON access_tokens(invitation_id,expires_at);
                    CREATE INDEX IF NOT EXISTS idx_access_tokens_expiry ON access_tokens(expires_at);
                    CREATE INDEX IF NOT EXISTS idx_auth_tokens_expiry ON auth_tokens(expires_at);
                    CREATE INDEX IF NOT EXISTS idx_guest_messages_invitation ON guest_messages(invitation_id,created_at DESC);
                    """)
                    user_columns={row["name"] for row in db.execute("PRAGMA table_info(users)")}
                    if "role" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'customer'")
                    if "email_verified" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
                    if "plan" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
                    if "upload_enabled" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN upload_enabled INTEGER NOT NULL DEFAULT 1")
                    if "password_algo" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN password_algo TEXT NOT NULL DEFAULT 'pbkdf2-sha256-v1'")
                    if "mfa_secret" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN mfa_secret TEXT")
                    if "mfa_enabled" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN mfa_enabled INTEGER NOT NULL DEFAULT 0")
                    if "deleted_at" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN deleted_at INTEGER")
                    if "deletion_scheduled_at" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN deletion_scheduled_at INTEGER")
                    if "privacy_json" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN privacy_json TEXT NOT NULL DEFAULT '{}'")
                    if "studio_name" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN studio_name TEXT NOT NULL DEFAULT ''")
                    if "white_label_json" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN white_label_json TEXT NOT NULL DEFAULT '{}'")
                    session_columns={row["name"] for row in db.execute("PRAGMA table_info(sessions)")}
                    if "user_agent" not in session_columns: db.execute("ALTER TABLE sessions ADD COLUMN user_agent TEXT NOT NULL DEFAULT ''")
                    if "ip_address" not in session_columns: db.execute("ALTER TABLE sessions ADD COLUMN ip_address TEXT NOT NULL DEFAULT ''")
                    if "last_seen_at" not in session_columns: db.execute("ALTER TABLE sessions ADD COLUMN last_seen_at INTEGER NOT NULL DEFAULT 0")
                    if "device_name" not in session_columns: db.execute("ALTER TABLE sessions ADD COLUMN device_name TEXT NOT NULL DEFAULT ''")
                    if "id" not in session_columns: db.execute("ALTER TABLE sessions ADD COLUMN id TEXT NOT NULL DEFAULT ''")
                    if "csrf_hash" not in session_columns: db.execute("ALTER TABLE sessions ADD COLUMN csrf_hash TEXT NOT NULL DEFAULT ''")
                    db.execute("UPDATE sessions SET id=token_hash WHERE id IS NULL OR id='' ")
                    columns={row["name"] for row in db.execute("PRAGMA table_info(invitations)")}
                    if "owner_id" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN owner_id TEXT")
                    if "archived" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
                    if "views" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN views INTEGER NOT NULL DEFAULT 0")
                    if "last_client_id" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN last_client_id TEXT")
                    if "last_mutation_id" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN last_mutation_id TEXT")
                    if "access_mode" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN access_mode TEXT NOT NULL DEFAULT 'unlisted'")
                    if "access_password_hash" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN access_password_hash TEXT")
                    if "access_password_salt" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN access_password_salt TEXT")
                    if "is_published" not in columns:
                        db.execute("ALTER TABLE invitations ADD COLUMN is_published INTEGER NOT NULL DEFAULT 0")
                        db.execute("UPDATE invitations SET is_published=1 WHERE EXISTS(SELECT 1 FROM publications p WHERE p.invitation_id=invitations.id)")
                    if "deleted_at" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN deleted_at INTEGER")
                    if "purge_at" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN purge_at INTEGER")
                    if "custom_domain" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN custom_domain TEXT")
                    if "publish_at" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN publish_at INTEGER")
                    if "unpublish_at" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN unpublish_at INTEGER")
                    if "expires_at" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN expires_at INTEGER")
                    if "gallery_access_password_hash" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN gallery_access_password_hash TEXT")
                    if "gallery_access_password_salt" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN gallery_access_password_salt TEXT")
                    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_invitations_custom_domain ON invitations(custom_domain) WHERE custom_domain IS NOT NULL AND custom_domain<>''")
                    db.execute("CREATE TRIGGER IF NOT EXISTS audit_events_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END")
                    db.execute("CREATE TRIGGER IF NOT EXISTS audit_events_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END")
                    guest_columns={row["name"] for row in db.execute("PRAGMA table_info(guests)")}
                    if "checked_in" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN checked_in INTEGER NOT NULL DEFAULT 0")
                    if "checked_in_at" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN checked_in_at INTEGER")
                    if "token_hash" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN token_hash TEXT")
                    if "token_salt" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN token_salt TEXT NOT NULL DEFAULT ''")
                    if "token_version" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1")
                    if "token_expires_at" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN token_expires_at INTEGER")
                    if "token_revoked_at" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN token_revoked_at INTEGER")
                    if "email" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN email TEXT NOT NULL DEFAULT ''")
                    if "group_name" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN group_name TEXT NOT NULL DEFAULT ''")
                    if "household_id" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN household_id TEXT NOT NULL DEFAULT ''")
                    if "tags_json" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'")
                    if "table_name" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN table_name TEXT NOT NULL DEFAULT ''")
                    if "seat_label" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN seat_label TEXT NOT NULL DEFAULT ''")
                    if "delivery_status" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN delivery_status TEXT NOT NULL DEFAULT ''")
                    if "opened_at" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN opened_at INTEGER")
                    # Migrate V11 plaintext guest credentials to one-way hashes while keeping old links valid.
                    for guest in db.execute("SELECT id,token,token_hash FROM guests WHERE token_hash IS NULL OR token_hash='' ").fetchall():
                        legacy=str(guest["token"] or "")
                        if not legacy:continue
                        db.execute("UPDATE guests SET token_hash=?,token=? WHERE id=?",(hashlib.sha256(legacy.encode()).hexdigest(),"legacy-"+guest["id"],guest["id"]))
                    rsvp_columns={row["name"] for row in db.execute("PRAGMA table_info(rsvps)")}
                    if "answers_json" not in rsvp_columns: db.execute("ALTER TABLE rsvps ADD COLUMN answers_json TEXT NOT NULL DEFAULT '{}'")
                    asset_columns={row["name"] for row in db.execute("PRAGMA table_info(assets)")}
                    if "folder" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN folder TEXT NOT NULL DEFAULT ''")
                    if "tags_json" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'")
                    if "favorite" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
                    if "sha256" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN sha256 TEXT NOT NULL DEFAULT ''")
                    if "width" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN width INTEGER NOT NULL DEFAULT 0")
                    if "height" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN height INTEGER NOT NULL DEFAULT 0")
                    if "dominant_color" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN dominant_color TEXT NOT NULL DEFAULT ''")
                    if "object_id" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN object_id TEXT")
                    if "processing_state" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN processing_state TEXT NOT NULL DEFAULT 'ready'")
                    # Backfill the stored-object registry for V11 and earlier material rows.
                    legacy_assets=db.execute("SELECT a.path,a.sha256,a.mime,a.size,a.width,a.height,a.dominant_color,i.owner_id,COUNT(*) ref_count FROM assets a JOIN invitations i ON i.id=a.invitation_id WHERE a.object_id IS NULL OR a.object_id='' GROUP BY a.path,a.sha256,a.mime,a.size,a.width,a.height,a.dominant_color,i.owner_id").fetchall()
                    for legacy in legacy_assets:
                        object_id="legacy-"+hashlib.sha256(f"{legacy['owner_id']}|{legacy['path']}".encode()).hexdigest()[:32]
                        now_ms=int(time.time()*1000)
                        db.execute("INSERT OR IGNORE INTO stored_objects(id,owner_id,path,storage_key,sha256,mime,size,width,height,dominant_color,processing_state,quarantine_state,scan_status,ref_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,'ready','released','legacy',?,?,?)",(object_id,legacy["owner_id"] or "legacy",legacy["path"],legacy["path"],legacy["sha256"] or "",legacy["mime"],legacy["size"],legacy["width"],legacy["height"],legacy["dominant_color"],legacy["ref_count"],now_ms,now_ms))
                        db.execute("UPDATE assets SET object_id=? WHERE path=? AND (object_id IS NULL OR object_id='')",(object_id,legacy["path"]))
                    rsvp_columns={row["name"] for row in db.execute("PRAGMA table_info(rsvps)")}
                    if "guest_id" not in rsvp_columns: db.execute("ALTER TABLE rsvps ADD COLUMN guest_id TEXT")
                    if "normalized_name" not in rsvp_columns: db.execute("ALTER TABLE rsvps ADD COLUMN normalized_name TEXT NOT NULL DEFAULT ''")
                    if "updated_at" not in rsvp_columns: db.execute("ALTER TABLE rsvps ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0")
                    db.execute("UPDATE rsvps SET normalized_name=lower(trim(name)) WHERE normalized_name='' OR normalized_name IS NULL")
                    db.execute("UPDATE rsvps SET updated_at=created_at WHERE updated_at=0 OR updated_at IS NULL")
                    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_rsvps_guest_unique ON rsvps(invitation_id,guest_id) WHERE guest_id IS NOT NULL")
                    db.execute("CREATE INDEX IF NOT EXISTS idx_rsvps_name_lookup ON rsvps(invitation_id,normalized_name,created_at DESC)")
                    template_columns={row["name"] for row in db.execute("PRAGMA table_info(user_templates)")}
                    for column,definition in {
                        "description":"TEXT NOT NULL DEFAULT ''",
                        "tags_json":"TEXT NOT NULL DEFAULT '[]'",
                        "favorite":"INTEGER NOT NULL DEFAULT 0",
                        "current_version":"INTEGER NOT NULL DEFAULT 1",
                        "thumbnail_json":"TEXT NOT NULL DEFAULT '{}'",
                        "visibility":"TEXT NOT NULL DEFAULT 'private'",
                        "published_at":"INTEGER",
                        "marketplace_status":"TEXT NOT NULL DEFAULT 'draft'",
                        "license_type":"TEXT NOT NULL DEFAULT 'personal'",
                    }.items():
                        if column not in template_columns: db.execute(f"ALTER TABLE user_templates ADD COLUMN {column} {definition}")
                    comment_columns={row["name"] for row in db.execute("PRAGMA table_info(invitation_comments)")}
                    for column,definition in {
                        "page_id":"TEXT NOT NULL DEFAULT ''","parent_id":"TEXT NOT NULL DEFAULT ''","anchor_x":"REAL NOT NULL DEFAULT -1","anchor_y":"REAL NOT NULL DEFAULT -1",
                    }.items():
                        if column not in comment_columns:db.execute(f"ALTER TABLE invitation_comments ADD COLUMN {column} {definition}")
                    db.execute("CREATE INDEX IF NOT EXISTS idx_invitation_comments_parent ON invitation_comments(invitation_id,parent_id,created_at)")
                    approval_columns={row["name"] for row in db.execute("PRAGMA table_info(approval_requests)")}
                    for column,definition in {
                        "document_revision":"INTEGER NOT NULL DEFAULT 0","document_fingerprint":"TEXT NOT NULL DEFAULT ''","summary_json":"TEXT NOT NULL DEFAULT '{}'","decided_by":"TEXT NOT NULL DEFAULT ''","decided_at":"INTEGER",
                    }.items():
                        if column not in approval_columns:db.execute(f"ALTER TABLE approval_requests ADD COLUMN {column} {definition}")
                    backup_columns={row["name"] for row in db.execute("PRAGMA table_info(backup_runs)")}
                    for column,definition in {
                        "owner_id":"TEXT NOT NULL DEFAULT ''","initiated_by":"TEXT NOT NULL DEFAULT ''","archive_name":"TEXT NOT NULL DEFAULT ''","size_bytes":"INTEGER NOT NULL DEFAULT 0","error_text":"TEXT NOT NULL DEFAULT ''",
                    }.items():
                        if column not in backup_columns:db.execute(f"ALTER TABLE backup_runs ADD COLUMN {column} {definition}")
                    db.execute("CREATE INDEX IF NOT EXISTS idx_backup_runs_owner_time ON backup_runs(owner_id,created_at DESC)")
                    db.execute("CREATE TABLE IF NOT EXISTS material_folders(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, parent_id TEXT, name TEXT NOT NULL, relative_key TEXT NOT NULL, created_by TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, UNIQUE(invitation_id,relative_key))")
                    db.execute("CREATE INDEX IF NOT EXISTS idx_material_folders_invitation ON material_folders(invitation_id,relative_key)")
                    db.execute("CREATE TABLE IF NOT EXISTS material_import_jobs(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, owner_id TEXT NOT NULL, source_type TEXT NOT NULL, root_name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'queued', total_files INTEGER NOT NULL DEFAULT 0, processed_files INTEGER NOT NULL DEFAULT 0, failed_files INTEGER NOT NULL DEFAULT 0, total_bytes INTEGER NOT NULL DEFAULT 0, processed_bytes INTEGER NOT NULL DEFAULT 0, failures_json TEXT NOT NULL DEFAULT '[]', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, cancelled_at INTEGER)")
                    db.execute("CREATE INDEX IF NOT EXISTS idx_material_import_jobs_invitation ON material_import_jobs(invitation_id,created_at DESC)")
                    upload_columns={row["name"] for row in db.execute("PRAGMA table_info(upload_sessions)")}
                    if "folder" not in upload_columns: db.execute("ALTER TABLE upload_sessions ADD COLUMN folder TEXT NOT NULL DEFAULT ''")
                    if "import_job_id" not in upload_columns: db.execute("ALTER TABLE upload_sessions ADD COLUMN import_job_id TEXT NOT NULL DEFAULT ''")
                    # Backfill version history for templates created before versioning existed.
                    for row in db.execute("SELECT id,document_json,current_version,created_at FROM user_templates").fetchall():
                        if not db.execute("SELECT 1 FROM template_versions WHERE template_id=? LIMIT 1",(row["id"],)).fetchone():
                            version=max(1,int(row["current_version"] or 1));db.execute("INSERT OR IGNORE INTO template_versions(id,template_id,version,document_json,created_at) VALUES(?,?,?,?,?)",(str(uuid.uuid4()),row["id"],version,row["document_json"],row["created_at"]))
                    _SQLITE_SCHEMA_READY=True
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


_PG_SCHEMA_READY=False
_PG_SCHEMA_LOCK=threading.Lock()

class PostgresAdapter:
    def __init__(self, connection):self.connection=connection
    def _query(self,sql):
        sql=sql.replace("INSERT OR IGNORE INTO","INSERT INTO")
        sql=re.sub(r"\?", "%s", sql)
        if "INSERT INTO template_versions" in sql and "ON CONFLICT" not in sql and "VALUES" in sql:
            sql += " ON CONFLICT DO NOTHING"
        return sql
    def execute(self,sql,params=()):return self.connection.execute(self._query(sql),params)
    def commit(self):return self.connection.commit()
    def rollback(self):return self.connection.rollback()
    def close(self):return self.connection.close()

def _ensure_postgres_schema(connection):
    global _PG_SCHEMA_READY
    if _PG_SCHEMA_READY:return
    with _PG_SCHEMA_LOCK:
        if _PG_SCHEMA_READY:return
        schema=(ROOT/"postgres_schema.sql").read_text(encoding="utf-8")
        connection.execute(schema,prepare=False)
        # Backfill the V12 stored-object registry for existing PostgreSQL assets.
        connection.execute("""
            INSERT INTO stored_objects(id,owner_id,path,sha256,mime,size,width,height,dominant_color,processing_state,quarantine_state,scan_status,ref_count,created_at,updated_at)
            SELECT 'legacy-' || substr(md5(i.owner_id || '|' || a.path),1,32),i.owner_id,a.path,COALESCE(a.sha256,''),a.mime,a.size,
                   COALESCE(a.width,0),COALESCE(a.height,0),COALESCE(a.dominant_color,''),'ready','released','legacy',COUNT(*),MIN(a.created_at),MAX(a.created_at)
            FROM assets a JOIN invitations i ON i.id=a.invitation_id
            WHERE a.object_id IS NULL OR a.object_id=''
            GROUP BY i.owner_id,a.path,a.sha256,a.mime,a.size,a.width,a.height,a.dominant_color
            ON CONFLICT(path) DO NOTHING
        """,prepare=False)
        connection.execute("""
            UPDATE assets a SET object_id=s.id
            FROM stored_objects s
            WHERE a.path=s.path AND (a.object_id IS NULL OR a.object_id='')
        """,prepare=False)
        # Convert legacy personalized guest credentials to hashes without invalidating old links.
        legacy_guests=connection.execute("SELECT id,token FROM guests WHERE (token_hash IS NULL OR token_hash='') AND token IS NOT NULL AND token<>''").fetchall()
        for row in legacy_guests:
            token_hash=guest_token_hash(row["token"]);sentinel="legacy-"+row["id"]
            connection.execute("UPDATE guests SET token_hash=%s,token=%s WHERE id=%s",(token_hash,sentinel,row["id"]))
        connection.commit();_PG_SCHEMA_READY=True

@contextmanager
def connect_postgres():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("PostgreSQL is configured but psycopg is not installed. Install requirements-production.txt.") from exc
    connection=psycopg.connect(DATABASE_URL,row_factory=dict_row,autocommit=False)
    try:
        _ensure_postgres_schema(connection)
        adapter=PostgresAdapter(connection)
        yield adapter
        connection.commit()
    except Exception:
        connection.rollback();raise
    finally:connection.close()

@contextmanager
def connect():
    if DATABASE_KIND=="postgresql":
        with connect_postgres() as db:yield db
    else:
        with connect_sqlite() as db:yield db

def write_audit_event(user_id, action, target_type="", target_id="", metadata=None, ip_address="system"):
    now=int(time.time()*1000);meta=json.dumps(metadata or {},ensure_ascii=False,sort_keys=True,separators=(",",":"))[:20000]
    with connect() as db:
        previous=db.execute("SELECT event_hash FROM audit_events ORDER BY created_at DESC,id DESC LIMIT 1").fetchone();previous_hash=previous["event_hash"] if previous else ""
        event_id=str(uuid.uuid4());payload=f"{event_id}|{user_id or ''}|{action}|{target_type}|{target_id}|{meta}|{str(ip_address)[:80]}|{previous_hash}|{now}";event_hash=hashlib.sha256(payload.encode()).hexdigest()
        db.execute("INSERT INTO audit_events(id,user_id,action,target_type,target_id,metadata_json,ip_address,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(event_id,user_id,action,target_type,target_id,meta,str(ip_address)[:80],previous_hash,event_hash,now))
    return event_id


_AI_AGENT_SERVICE = None
def get_ai_agent_service():
    global _AI_AGENT_SERVICE
    if _AI_AGENT_SERVICE is None:
        ensure_agent_schema(connect)
        def agent_audit(user_id, action, target_type, target_id, metadata):
            write_audit_event(user_id, action, target_type, target_id, metadata, "ai-agent")
        def agent_asset_reader(invitation_id, user_id, asset_id):
            with connect() as db:
                row=db.execute("SELECT a.path,a.mime FROM assets a WHERE a.id=? AND a.invitation_id=?",(asset_id,invitation_id)).fetchone()
            if not row:raise ValueError("Reference asset not found")
            raw=read_stored_asset_bytes(row["path"])
            if raw is None:raise ValueError("Reference asset bytes are unavailable")
            return {"raw":raw,"mime":row["mime"]}
        _AI_AGENT_SERVICE = AgentService(connect, AgentConfig.from_environment(), audit=agent_audit, asset_reader=agent_asset_reader)
    return _AI_AGENT_SERVICE

_PLATFORM_V32_SERVICE = None
def get_platform_v32_service():
    global _PLATFORM_V32_SERVICE
    if _PLATFORM_V32_SERVICE is None:
        ensure_platform_schema(connect)
        def platform_audit(user_id, action, target_type, target_id, metadata):
            write_audit_event(user_id, action, target_type, target_id, metadata, "platform-v32")
        def platform_upload_validator(raw, mime, name):
            validate_material_request(mime,len(raw));validate_material_bytes(raw,mime)
            scan=scan_material_bytes(raw,mime,name)
            if not scan.get("clean"):raise ValueError("Uploaded material did not pass malware scanning")
            return inspect_image_bytes(raw,mime) if str(mime).startswith("image/") else {"width":0,"height":0,"dominantColor":""}
        _PLATFORM_V32_SERVICE = PlatformService(
            connect, ROOT, DATA, MEDIA_SIGNING_SECRET,
            audit=platform_audit, json_logs=JSON_LOGS,
            config=PlatformConfig.from_environment(),
            upload_validator=platform_upload_validator,
        )
    return _PLATFORM_V32_SERVICE

_FUTURE_V52_SERVICE = None
def get_future_v52_service():
    global _FUTURE_V52_SERVICE
    if _FUTURE_V52_SERVICE is None:
        ensure_future_schema(connect)
        def future_audit(user_id, action, target_type, target_id, metadata):
            write_audit_event(user_id, action, target_type, target_id, metadata, "future-platform-v52")
        _FUTURE_V52_SERVICE = FuturePlatformService(
            connect,
            get_platform_v32_service(),
            ai_service=get_ai_agent_service(),
            audit=future_audit,
        )
    return _FUTURE_V52_SERVICE

def build_studio_archive(owner_id, include_media=True):
    """Build a private, reconstructable studio archive for one account."""
    with connect() as db:
        user=db.execute("SELECT id,email,studio_name FROM users WHERE id=? AND deleted_at IS NULL",(owner_id,)).fetchone()
        if not user:raise ValueError("Studio account not found")
        invitations=[dict(r) for r in db.execute("SELECT id,slug,draft_json,updated_at,archived,views,access_mode,is_published FROM invitations WHERE owner_id=? ORDER BY updated_at DESC",(owner_id,)).fetchall()]
        invite_ids=[row["id"] for row in invitations]
        assets=[]
        if invite_ids:
            q=','.join('?' for _ in invite_ids)
            assets=[dict(r) for r in db.execute(f"SELECT a.*,s.path object_path FROM assets a LEFT JOIN stored_objects s ON s.id=a.object_id WHERE a.invitation_id IN ({q})",invite_ids).fetchall()]
        resources=[dict(r) for r in db.execute("SELECT * FROM studio_resources WHERE owner_id=? ORDER BY updated_at DESC",(owner_id,)).fetchall()]
        releases=[dict(r) for r in db.execute("SELECT * FROM studio_releases WHERE owner_id=? ORDER BY updated_at DESC",(owner_id,)).fetchall()]
        pins=[dict(r) for r in db.execute("SELECT p.* FROM invitation_studio_release_pins p JOIN invitations i ON i.id=p.invitation_id WHERE i.owner_id=?",(owner_id,)).fetchall()]
        governance=db.execute("SELECT policy_json,updated_at FROM studio_governance WHERE owner_id=?",(owner_id,)).fetchone()
        backup_policy=db.execute("SELECT * FROM studio_backup_policies WHERE owner_id=?",(owner_id,)).fetchone()
        bulk_jobs=[dict(r) for r in db.execute("SELECT * FROM studio_bulk_jobs WHERE owner_id=? ORDER BY created_at DESC LIMIT 100",(owner_id,)).fetchall()]
    for item in resources:
        for key in ("payload_json","governance_json"):
            try:item[key[:-5]]=json.loads(item.pop(key) or "{}")
            except Exception:item[key[:-5]]={}
    for item in releases:
        try:item["manifest"]=json.loads(item.pop("manifest_json") or "[]")
        except Exception:item["manifest"]=[]
    for item in bulk_jobs:
        for key in ("selection_json","result_json"):
            try:item[key[:-5]]=json.loads(item.pop(key) or "{}")
            except Exception:item[key[:-5]]={}
    try:governance_export={"policy":json.loads(governance["policy_json"] or "{}"),"updatedAt":governance["updated_at"]} if governance else {}
    except Exception:governance_export={}
    payload={
        "schema":"einvite-studio-archive-v27","exportedAt":int(time.time()*1000),
        "account":{"id":user["id"],"email":user["email"],"studioName":user["studio_name"] or ""},
        "invitations":invitations,"assets":[{k:v for k,v in asset.items() if k!="tags_json"} for asset in assets],
        "studioResources":resources,"studioReleases":releases,"studioReleasePins":pins,
        "studioGovernance":governance_export,"backupPolicy":dict(backup_policy) if backup_policy else {},"studioBulkJobs":bulk_jobs,
    }
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("account.json",json.dumps(payload,ensure_ascii=False,indent=2))
        if include_media:
            seen=set()
            for asset in assets:
                path=asset.get("object_path") or asset.get("path")
                if not path or path in seen:continue
                seen.add(path)
                try:raw=read_stored_asset_bytes(path)
                except Exception:raw=None
                if raw:archive.writestr(f"media/{Path(path).name}",raw)
    return buffer.getvalue(),payload

def prune_studio_backups(owner_id, retention_count):
    retention=max(1,min(30,int(retention_count or 7)))
    with connect() as db:
        rows=db.execute("SELECT id,archive_name FROM backup_runs WHERE owner_id=? AND status='completed' ORDER BY created_at DESC",(owner_id,)).fetchall()
        stale=rows[retention:]
        for row in stale:
            name=Path(str(row["archive_name"] or "")).name
            if name:
                try:(BACKUPS/name).unlink(missing_ok=True)
                except OSError:pass
            db.execute("DELETE FROM backup_runs WHERE id=? AND owner_id=?",(row["id"],owner_id))

def studio_backup_lock(owner_id):
    with STUDIO_BACKUP_LOCKS_GUARD:return STUDIO_BACKUP_LOCKS.setdefault(str(owner_id),threading.Lock())

def run_studio_backup(owner_id, initiated_by="", kind="manual", include_media=True):
    lock=studio_backup_lock(owner_id)
    if not lock.acquire(blocking=False):return {"id":"","status":"busy","createdAt":int(time.time()*1000),"error":"A studio backup is already running."}
    run_id=str(uuid.uuid4());now=int(time.time()*1000);archive_name=f"studio-backup-{owner_id[:8]}-{now}-{run_id[:8]}.zip"
    try:
        with connect() as db:
            db.execute("INSERT INTO backup_runs(id,kind,status,detail_json,created_at,owner_id,initiated_by,archive_name) VALUES(?,?, 'running','{}',?,?,?,?)",(run_id,kind,now,owner_id,initiated_by,archive_name))
        raw,payload=build_studio_archive(owner_id,include_media=include_media)
        target=BACKUPS/archive_name;tmp=target.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(target)
        completed=int(time.time()*1000);detail={"invitations":len(payload.get("invitations",[])),"resources":len(payload.get("studioResources",[])),"releases":len(payload.get("studioReleases",[])),"includeMedia":bool(include_media)}
        with connect() as db:
            db.execute("UPDATE backup_runs SET status='completed',detail_json=?,completed_at=?,size_bytes=? WHERE id=?",(json.dumps(detail),completed,len(raw),run_id))
            policy=db.execute("SELECT retention_count FROM studio_backup_policies WHERE owner_id=?",(owner_id,)).fetchone()
            db.execute("UPDATE studio_backup_policies SET last_run_at=?,next_run_at=CASE WHEN enabled=1 THEN ? + interval_hours*3600000 ELSE NULL END WHERE owner_id=?",(completed,completed,owner_id))
        prune_studio_backups(owner_id,policy["retention_count"] if policy else 7)
        write_audit_event(owner_id,"studio.backup_completed","backup",run_id,{"sizeBytes":len(raw),"includeMedia":bool(include_media),"kind":kind},"scheduler" if kind=="scheduled" else "local")
        return {"id":run_id,"status":"completed","archiveName":archive_name,"sizeBytes":len(raw),"createdAt":now,"completedAt":completed,"detail":detail}
    except Exception as exc:
        completed=int(time.time()*1000);message=str(exc)[:1000]
        with connect() as db:db.execute("UPDATE backup_runs SET status='failed',completed_at=?,error_text=? WHERE id=?",(completed,message,run_id))
        write_audit_event(owner_id,"studio.backup_failed","backup",run_id,{"includeMedia":bool(include_media),"kind":kind,"error":message},"scheduler" if kind=="scheduled" else "local")
        return {"id":run_id,"status":"failed","archiveName":archive_name,"createdAt":now,"completedAt":completed,"error":message}
    finally:
        lock.release()

def process_due_studio_backups(limit=3):
    now=int(time.time()*1000)
    with connect() as db:
        rows=db.execute("SELECT owner_id,include_media FROM studio_backup_policies WHERE enabled=1 AND (next_run_at IS NULL OR next_run_at<=?) ORDER BY COALESCE(next_run_at,0) LIMIT ?",(now,max(1,min(10,int(limit))))).fetchall()
    for row in rows:run_studio_backup(row["owner_id"],"scheduler","scheduled",bool(row["include_media"]))


MATERIAL_TYPES={
    "image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/gif":".gif",
    "audio/mpeg":".mp3","audio/mp4":".m4a","video/mp4":".mp4","video/webm":".webm",
    # Custom fonts are accepted only through the dedicated font pipeline. The
    # normalized stored representation is WOFF2 so invitation payloads remain
    # compact and browser delivery is deterministic.
    "font/woff2":".woff2",
}
FONT_SOURCE_MIMES={
    "font/ttf","application/x-font-ttf","application/font-sfnt","font/sfnt",
    "font/otf","application/x-font-opentype","application/vnd.ms-opentype",
    "font/woff2","application/font-woff2","application/woff2",
    "application/octet-stream",
}
MAX_CUSTOM_FONT_SOURCE_BYTES=8_000_000
MAX_CUSTOM_FONT_GLYPHS=65_535
MAX_CUSTOM_FONT_TABLES=128

def material_size_limit(mime):
    if str(mime).startswith("font/"):return MAX_CUSTOM_FONT_SOURCE_BYTES
    return 50_000_000 if str(mime).startswith("video/") else 25_000_000 if str(mime).startswith("audio/") else 15_000_000

def validate_material_request(mime,size,allow_font=False):
    mime=str(mime or "").lower();size=int(size or 0)
    if mime.startswith("font/") and not allow_font:raise ValueError("Font files must use the dedicated custom-font upload")
    if mime not in MATERIAL_TYPES:raise ValueError("Unsupported material type")
    limit=material_size_limit(mime)
    if size<=0:raise ValueError("Empty material upload")
    if size>limit:raise ValueError(f"Material exceeds {limit//1_000_000} MB")
    return mime,limit

def acquire_stored_object(owner_id, asset_id, raw, mime, preferred_path=None, scan_name="upload", allow_font=False):
    """Validate/quarantine a material and acquire one physical stored-object reference."""
    validate_material_request(mime,len(raw),allow_font=allow_font);validate_material_bytes(raw,mime)
    quarantine=QUARANTINE/f"{asset_id}.part";quarantine.write_bytes(raw)
    try:
        scan=scan_material_bytes(raw,mime,scan_name)
        metadata=inspect_image_bytes(raw,mime) if mime.startswith("image/") else {"width":0,"height":0,"dominantColor":""}
        digest=hashlib.sha256(raw).hexdigest();now=int(time.time()*1000)
        with connect() as db:
            existing=db.execute("SELECT id,path,sha256,mime,size,width,height,dominant_color FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime=? AND processing_state='ready' ORDER BY created_at LIMIT 1",(owner_id,digest,len(raw),mime)).fetchone()
            if existing:
                db.execute("UPDATE stored_objects SET ref_count=(SELECT COUNT(*) FROM assets WHERE object_id=?)+1,updated_at=? WHERE id=?",(existing["id"],now,existing["id"]))
                return {"id":existing["id"],"path":existing["path"],"sha256":existing["sha256"],"mime":existing["mime"],"size":existing["size"],"width":existing["width"],"height":existing["height"],"dominantColor":existing["dominant_color"],"duplicate":True,"scanStatus":scan.get("status","not-configured")}
        path=Path(str(preferred_path or (asset_id+MATERIAL_TYPES[mime]))).name
        storage_key=store_asset_bytes(path,raw,mime,owner_id)
        object_id=str(uuid.uuid4())
        try:
            with connect() as db:
                db.execute("INSERT INTO stored_objects(id,owner_id,path,storage_key,sha256,mime,size,width,height,dominant_color,processing_state,quarantine_state,scan_status,ref_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,'ready','released',?,1,?,?)",(object_id,owner_id,path,storage_key,digest,mime,len(raw),metadata["width"],metadata["height"],metadata["dominantColor"],scan.get("status","not-configured"),now,now))
        except Exception:
            delete_stored_asset(path,digest);raise
        return {"id":object_id,"path":path,"sha256":digest,"mime":mime,"size":len(raw),**metadata,"duplicate":False,"scanStatus":scan.get("status","not-configured")}
    finally:
        try:quarantine.unlink(missing_ok=True)
        except OSError:pass

def register_existing_stored_object(owner_id, preferred_path, raw, mime, scan_name="upload"):
    """Validate and register a direct-uploaded object without uploading it twice."""
    path=Path(str(preferred_path)).name
    if not path:raise ValueError("Invalid uploaded object path")
    validate_material_bytes(raw,mime)
    scan=scan_material_bytes(raw,mime,scan_name)
    if scan.get("status") in {"infected","blocked","error"}:raise ValueError(scan.get("message") or "The upload failed its security scan")
    metadata=inspect_image_bytes(raw,mime) if mime.startswith("image/") else {"width":0,"height":0,"dominantColor":""}
    digest=hashlib.sha256(raw).hexdigest();now=int(time.time()*1000)
    with connect() as db:
        existing=db.execute("SELECT id,path,sha256,mime,size,width,height,dominant_color FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime=? AND processing_state='ready' ORDER BY created_at LIMIT 1",(owner_id,digest,len(raw),mime)).fetchone()
        if existing:
            db.execute("UPDATE stored_objects SET ref_count=(SELECT COUNT(*) FROM assets WHERE object_id=?)+1,updated_at=? WHERE id=?",(existing["id"],now,existing["id"]))
            result={"id":existing["id"],"path":existing["path"],"sha256":existing["sha256"],"mime":existing["mime"],"size":existing["size"],"width":existing["width"],"height":existing["height"],"dominantColor":existing["dominant_color"],"duplicate":True,"scanStatus":scan.get("status","not-configured")}
        else:
            object_id=str(uuid.uuid4())
            db.execute("INSERT INTO stored_objects(id,owner_id,path,storage_key,sha256,mime,size,width,height,dominant_color,processing_state,quarantine_state,scan_status,ref_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,'ready','released',?,1,?,?)",(object_id,owner_id,path,path,digest,mime,len(raw),metadata["width"],metadata["height"],metadata["dominantColor"],scan.get("status","not-configured"),now,now))
            result={"id":object_id,"path":path,"sha256":digest,"mime":mime,"size":len(raw),**metadata,"duplicate":False,"scanStatus":scan.get("status","not-configured")}
    if result["duplicate"] and result["path"]!=path:
        delete_stored_asset(path,digest)
    return result

def sanitize_material_folder(value):
    original=str(value or "").replace("\\","/").strip()
    if not original:return ""
    if original.startswith("/") or re.match(r"^[A-Za-z]:",original):raise ValueError("Invalid material folder")
    raw=original.strip("/")
    parts=[]
    for part in raw.split("/"):
        part=re.sub(r"[\x00-\x1f\x7f]+"," ",part).strip()
        if part in {"",".",".."}:
            if part in {".",".."}:raise ValueError("Material folders cannot contain traversal segments")
            continue
        part=re.sub(r'[/:*?"<>|]+',"-",part).strip(" .")[:120]
        if not part:raise ValueError("Invalid material folder name")
        parts.append(part)
        if len(parts)>24:raise ValueError("Material folder nesting is too deep")
    result="/".join(parts)
    if len(result)>1000:raise ValueError("Material folder path is too long")
    return result

def validate_material_zip_entry_path(value):
    name=str(value or "").replace("\\","/")
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:",name) or any(part in {"..","."} for part in name.split("/") if part):
        raise ValueError("ZIP path traversal was rejected")
    return sanitize_material_folder(name.rstrip("/"))

def ensure_material_folder_chain(db, invite_id, user_id, folder):
    key=sanitize_material_folder(folder)
    if not key:return None
    parent_id=None;current=[];now=int(time.time()*1000)
    for segment in key.split("/"):
        current.append(segment);relative_key="/".join(current)
        row=db.execute("SELECT id FROM material_folders WHERE invitation_id=? AND relative_key=?",(invite_id,relative_key)).fetchone()
        if row:parent_id=row["id"];continue
        folder_id=str(uuid.uuid4())
        db.execute("INSERT INTO material_folders(id,invitation_id,parent_id,name,relative_key,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(folder_id,invite_id,parent_id,segment,relative_key,user_id,now,now))
        parent_id=folder_id
    return parent_id

def update_material_import_job(job_id, processed_bytes=0, success=True, failure=None):
    if not job_id:return
    now=int(time.time()*1000)
    with connect() as db:
        row=db.execute("SELECT * FROM material_import_jobs WHERE id=?",(job_id,)).fetchone()
        if not row or row["status"] in {"cancelled","completed"}:return
        failures=[]
        try:failures=json.loads(row["failures_json"] or "[]")
        except Exception:failures=[]
        if failure and len(failures)<200:failures.append(failure)
        processed_files=int(row["processed_files"] or 0)+1;failed_files=int(row["failed_files"] or 0)+(0 if success else 1)
        status="completed" if processed_files>=int(row["total_files"] or 0) else "running"
        db.execute("UPDATE material_import_jobs SET status=?,processed_files=?,failed_files=?,processed_bytes=?,failures_json=?,updated_at=? WHERE id=?",(status,processed_files,failed_files,int(row["processed_bytes"] or 0)+max(0,int(processed_bytes or 0)),json.dumps(failures,ensure_ascii=False),now,job_id))

def insert_asset_reference(invite_id, asset_id, name, stored, folder=""):
    now=int(time.time()*1000);folder=sanitize_material_folder(folder)
    try:
        with connect() as db:
            scope=db.execute("SELECT workspace_id,owner_id FROM invitations WHERE id=?",(invite_id,)).fetchone();workspace_id=(scope["workspace_id"] if scope else None) or (get_platform_v32_service().workspace_for_user(scope["owner_id"])["id"] if scope else "")
            if folder and scope:ensure_material_folder_chain(db,invite_id,scope["owner_id"] or "",folder)
            db.execute("INSERT INTO assets(id,invitation_id,name,mime,path,size,created_at,folder,tags_json,favorite,sha256,width,height,dominant_color,object_id,processing_state,workspace_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                asset_id,invite_id,str(name or "upload")[:180],stored["mime"],stored["path"],int(stored["size"]),now,folder,"[]",0,stored.get("sha256","") or "",int(stored.get("width",0) or 0),int(stored.get("height",0) or 0),stored.get("dominantColor","") or "",stored.get("id"),"ready",workspace_id))
            if stored.get("id"):
                db.execute("UPDATE stored_objects SET ref_count=(SELECT COUNT(*) FROM assets WHERE object_id=?),updated_at=? WHERE id=?",(stored["id"],now,stored["id"]))
    except Exception:
        # A new physical object must not be stranded if creating its first logical
        # asset reference fails. Shared objects are retained and their reference
        # count is reconciled to the actual logical asset rows.
        if stored.get("id"):
            orphan=False
            with connect() as db:
                refs=int(db.execute("SELECT COUNT(*) count FROM assets WHERE object_id=?",(stored["id"],)).fetchone()["count"] or 0)
                if refs<=0 and not stored.get("duplicate"):
                    db.execute("DELETE FROM stored_objects WHERE id=?",(stored["id"],));orphan=True
                else:
                    db.execute("UPDATE stored_objects SET ref_count=?,updated_at=? WHERE id=?",(refs,int(time.time()*1000),stored["id"]))
            if orphan:delete_stored_asset(stored.get("path",""),stored.get("sha256",""))
        raise
    return {"id":asset_id,"url":asset_public_url(stored["path"]),"responsiveBase":responsive_asset_url(stored["path"]),"size":int(stored["size"]),"duplicate":bool(stored.get("duplicate")),"width":int(stored.get("width",0) or 0),"height":int(stored.get("height",0) or 0),"dominantColor":stored.get("dominantColor","") or "","processingState":"ready","scanStatus":stored.get("scanStatus","not-configured")}


def release_stored_object_references(db, object_ids):
    """Reconcile ref counts after asset rows are removed and return physical objects to purge."""
    purge=[]
    for object_id in {str(x) for x in object_ids if x}:
        row=db.execute("SELECT id,path,sha256 FROM stored_objects WHERE id=?",(object_id,)).fetchone()
        if not row:continue
        remaining=db.execute("SELECT COUNT(*) count FROM assets WHERE object_id=?",(object_id,)).fetchone()["count"]
        if int(remaining or 0)<=0:
            db.execute("DELETE FROM stored_objects WHERE id=?",(object_id,));purge.append((row["path"],row["sha256"]))
        else:db.execute("UPDATE stored_objects SET ref_count=?,updated_at=? WHERE id=?",(int(remaining),int(time.time()*1000),object_id))
    return purge


def queue_physical_deletions(items):
    """Persist physical deletion work only after logical reference changes commit."""
    normalized={(Path(str(path or "")).name,str(digest or "")) for path,digest in (items or []) if Path(str(path or "")).name}
    if not normalized:return 0
    now=int(time.time()*1000)
    with connect() as db:
        for path,digest in normalized:
            payload=json.dumps({"path":path,"sha256":digest},sort_keys=True,separators=(",",":"))
            existing=db.execute("SELECT id FROM background_jobs WHERE kind='storage.delete' AND state IN ('queued','running') AND payload_json=? LIMIT 1",(payload,)).fetchone()
            if not existing:db.execute("INSERT INTO background_jobs(id,kind,payload_json,state,attempts,available_at,created_at,updated_at) VALUES(?,?,?,'queued',0,?,?,?)",(str(uuid.uuid4()),"storage.delete",payload,now,now,now))
    if not BACKGROUND_MEDIA_ENABLED:process_storage_delete_jobs(limit=len(normalized))
    return len(normalized)

def process_storage_delete_jobs(limit=25):
    processed=0
    for _ in range(max(0,int(limit))):
        now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT id,payload_json,attempts FROM background_jobs WHERE kind='storage.delete' AND state='queued' AND available_at<=? ORDER BY created_at LIMIT 1",(now,)).fetchone()
            if not row:break
            db.execute("UPDATE background_jobs SET state='running',locked_at=?,attempts=attempts+1,updated_at=? WHERE id=?",(now,now,row["id"]))
        try:
            payload=json.loads(row["payload_json"] or "{}");delete_stored_asset(payload.get("path",""),payload.get("sha256",""))
            with connect() as db:db.execute("UPDATE background_jobs SET state='done',locked_at=NULL,last_error='',updated_at=? WHERE id=?",(int(time.time()*1000),row["id"]))
        except Exception as exc:
            delay=min(3600,30*(2**min(int(row["attempts"] or 0),6)));available=int(time.time()*1000)+delay*1000
            with connect() as db:db.execute("UPDATE background_jobs SET state='queued',locked_at=NULL,last_error=?,available_at=?,updated_at=? WHERE id=?",(str(exc)[:1000],available,int(time.time()*1000),row["id"]))
        processed+=1
    return processed

def managed_media_path(value):
    raw=str(value or "").strip()
    if not raw:return ""
    parsed=urlparse(raw);path=parsed.path
    for prefix in ("/uploads/","/api/image/","/api/media/"):
        if path.startswith(prefix):return Path(unquote(path[len(prefix):])).name
    if OBJECT_STORAGE_PUBLIC_BASE_URL and raw.startswith(OBJECT_STORAGE_PUBLIC_BASE_URL+"/"):
        return Path(unquote(parsed.path)).name
    return ""

def document_references_media(document_json, path):
    clean=Path(str(path or "")).name
    if not clean:return False
    text=str(document_json or "")
    return clean in text and (f"/uploads/{clean}" in text or f"/api/image/{clean}" in text or (OBJECT_STORAGE_PUBLIC_BASE_URL and clean in text))

def protected_gallery_media_paths(document):
    """Return managed media used exclusively by gallery-only hero objects."""
    if not isinstance(document,dict):return set()
    objects=document.get("objects") if isinstance(document.get("objects"),dict) else {}
    candidates={}
    for object_id,obj in objects.items():
        if not isinstance(obj,dict) or obj.get("type")!="image" or obj.get("showInGallery") is False or obj.get("showInHero") is not False:continue
        clean=managed_media_path(obj.get("src"))
        if clean:candidates.setdefault(clean,[]).append(object_id)
    if not candidates:return set()
    result=set()
    for clean,ids in candidates.items():
        clone=json.loads(json.dumps(document))
        for object_id in ids:
            target=(clone.get("objects") or {}).get(object_id)
            if isinstance(target,dict):
                target["src"]="";target["responsiveBase"]=""
        if not document_references_media(json.dumps(clone,ensure_ascii=False),clean):result.add(clean)
    return result

def gallery_access_token_valid(db,invitation_id,token):
    if not token:return False
    now=int(time.time()*1000);token_hash=hashlib.sha256(str(token).encode()).hexdigest()
    return db.execute("SELECT 1 FROM gallery_access_tokens WHERE token_hash=? AND invitation_id=? AND expires_at>?",(token_hash,invitation_id,now)).fetchone() is not None

def apply_gallery_access(document,invitation_id,authorized=False):
    if not isinstance(document,dict):return document
    protected=protected_gallery_media_paths(document)
    protection=document.get("galleryProtection") if isinstance(document.get("galleryProtection"),dict) else {}
    if not protection.get("enabled") or not protected:return document
    clone=json.loads(json.dumps(document))
    clone.setdefault("galleryProtection",{})["locked"]=not authorized
    for obj in (clone.get("objects") or {}).values():
        if not isinstance(obj,dict):continue
        clean=managed_media_path(obj.get("src"))
        if clean not in protected:continue
        if authorized:
            obj["src"]=signed_media_url(clean,invitation_id)
            obj["responsiveBase"]=signed_media_url(clean,invitation_id)
        else:
            obj["showInGallery"]=False
            obj["src"]=""
            obj["responsiveBase"]=""
    return clone

def rewrite_document_media_urls(document, invitation_id):
    """Replace managed media URLs with short-lived signed first-party URLs.

    Handles both plain URL fields and URLs embedded inside safe rich-text/CSS
    strings so protected invitations do not break when a legacy document stored
    an image reference inside markup.
    """
    expires=int(time.time())+MEDIA_URL_TTL_SECONDS
    def signed_for(clean, query=''):
        signed=signed_media_url(clean,invitation_id,expires)
        params=parse_qs(query)
        extras=[]
        for key in ("w","format"):
            for item in params.get(key,[]):extras.append((key,item))
        if extras:signed+="&"+"&".join(f"{quote(k)}={quote(str(v))}" for k,v in extras)
        return signed
    pattern=re.compile(r"(?P<url>/(?:uploads|api/image)/(?P<path>[^\s\"'()<>?]+)(?:\?(?P<query>[^\s\"'()<>#]*))?)",re.I)
    def walk(value):
        if isinstance(value,dict):return {k:walk(v) for k,v in value.items()}
        if isinstance(value,list):return [walk(v) for v in value]
        if not isinstance(value,str):return value
        clean=managed_media_path(value)
        if clean:
            parsed=urlparse(value);return signed_for(clean,parsed.query)
        return pattern.sub(lambda match:signed_for(Path(unquote(match.group("path"))).name,match.group("query") or ""),value)
    return walk(document)

def derivative_format(requested):
    value=str(requested or "webp").lower()
    if value not in IMAGE_FORMAT_ALLOWLIST:raise ValueError("Unsupported responsive image format")
    try:
        from PIL import features
        if value=="avif" and not features.check("avif"):return "webp"
    except Exception:
        if value=="avif":return "webp"
    return value

def generate_image_derivative(path, width, requested="webp"):
    clean=Path(str(path or "")).name
    if int(width) not in IMAGE_WIDTH_ALLOWLIST:raise ValueError("Unsupported responsive image width")
    source=read_stored_asset_bytes(clean)
    if source is None:raise FileNotFoundError(clean)
    source_mime=mimetypes.guess_type(clean)[0] or "application/octet-stream"
    if not source_mime.startswith("image/"):raise TypeError("Responsive derivatives are available for images only")
    actual=derivative_format(requested);source_hash=hashlib.sha256(source).hexdigest();tag=source_hash[:20]
    suffix={"webp":".webp","jpeg":".jpg","jpg":".jpg","png":".png","avif":".avif"}[actual]
    cache_key=hashlib.sha256(f"{clean}|{tag}|{int(width)}|{actual}".encode()).hexdigest();cached=IMAGE_CACHE/(cache_key+suffix)
    content_type={"webp":"image/webp","jpeg":"image/jpeg","jpg":"image/jpeg","png":"image/png","avif":"image/avif"}[actual]
    if cached.is_file():
        body=cached.read_bytes();return body,content_type,source_hash,cached.stat().st_mtime
    from PIL import Image,ImageOps
    Image.MAX_IMAGE_PIXELS=MAX_IMAGE_MEGAPIXELS*1_000_000
    with warnings.catch_warnings():
        warnings.simplefilter("error",Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(source)) as probe:probe.verify()
        with Image.open(io.BytesIO(source)) as image:
            image=ImageOps.exif_transpose(image)
            if getattr(image,"is_animated",False):image.seek(0)
            if image.width>MAX_IMAGE_DIMENSION or image.height>MAX_IMAGE_DIMENSION or image.width*image.height>MAX_IMAGE_MEGAPIXELS*1_000_000:raise ValueError("Image exceeds responsive-processing safety limits")
            if image.width>int(width):
                height=max(1,round(image.height*(int(width)/image.width)));image=image.resize((int(width),height),Image.Resampling.LANCZOS)
            save_format={"jpg":"JPEG","jpeg":"JPEG","webp":"WEBP","png":"PNG","avif":"AVIF"}[actual]
            if save_format in {"JPEG","WEBP","AVIF"} and image.mode not in {"RGB","L"}:image=image.convert("RGB")
            out=io.BytesIO();kwargs={"quality":84,"optimize":True} if save_format in {"JPEG","WEBP","AVIF"} else {"optimize":True}
            # Generated derivatives intentionally omit original EXIF metadata by default.
            image.save(out,format=save_format,**kwargs);body=out.getvalue()
    try:cached.write_bytes(body);evict_image_cache()
    except OSError:pass
    return body,content_type,source_hash,time.time()

def pre_generate_common_derivatives(path,mime,source_hash=""):
    if not str(mime or "").startswith("image/") or str(mime).lower()=="image/gif":return
    # Keep upload latency bounded while warming the variants most commonly used by
    # phones, tablets and desktop invitation previews.
    for width in (320,768,1440):
        try:generate_image_derivative(path,width,"webp")
        except Exception:break

def cleanup_upload_sessions():
    now=int(time.time()*1000);paths=[]
    with connect() as db:
        rows=db.execute("SELECT temp_path FROM upload_sessions WHERE expires_at<=?",(now,)).fetchall();paths=[r["temp_path"] for r in rows]
        db.execute("DELETE FROM upload_sessions WHERE expires_at<=?",(now,))
    for value in paths:
        try:(QUARANTINE/Path(str(value)).name).unlink(missing_ok=True)
        except OSError:pass
    return len(paths)

def cleanup_expired_security_rows():
    """Remove expired credentials, apply due schedules, old trash and account deletions."""
    try: process_scheduled_publications()
    except Exception: pass
    try: process_scheduled_campaigns()
    except Exception: pass
    now=int(time.time()*1000);purge=[];purged_users=0
    with connect() as db:
        sessions=db.execute("DELETE FROM sessions WHERE expires_at<=?",(now,)).rowcount
        auth_tokens=db.execute("DELETE FROM auth_tokens WHERE expires_at<=?",(now,)).rowcount
        access_tokens=db.execute("DELETE FROM access_tokens WHERE expires_at<=?",(now,)).rowcount
        gallery_access_tokens=db.execute("DELETE FROM gallery_access_tokens WHERE expires_at<=?",(now,)).rowcount
        challenges=db.execute("DELETE FROM auth_challenges WHERE expires_at<=? OR used_at IS NOT NULL",(now,)).rowcount
        expired_invites=[r["id"] for r in db.execute("SELECT id FROM invitations WHERE purge_at IS NOT NULL AND purge_at<=?",(now,)).fetchall()]
        for invite_id in expired_invites:
            asset_rows=db.execute("SELECT object_id,path,sha256 FROM assets WHERE invitation_id=?",(invite_id,)).fetchall()
            db.execute("DELETE FROM rsvps WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM guest_messages WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM view_events WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM access_tokens WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM gallery_access_tokens WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM publications WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM assets WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM guests WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_collaborators WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_comments WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM approval_requests WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_review_policies WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM review_notifications WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM review_tasks WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_studio_release_pins WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM upload_sessions WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM material_import_jobs WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM material_folders WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitations WHERE id=?",(invite_id,))
            purge.extend(release_stored_object_references(db,[row["object_id"] for row in asset_rows]))
        db.execute("DELETE FROM deleted_items WHERE purge_at<=?",(now,))
        db.execute("DELETE FROM bandwidth_events WHERE created_at<?",(now-90*24*60*60*1000,))
        db.execute("DELETE FROM background_jobs WHERE state='done' AND updated_at<?",(now-14*24*60*60*1000,))
        db.execute("UPDATE background_jobs SET state='queued',locked_at=NULL,available_at=? WHERE state='running' AND locked_at<?",(now,now-30*60*1000))
        # Apply each account's configured retention period to guest-generated responses,
        # private wishes and analytics. Guest-list records are intentionally retained
        # because they are owner-managed operational records rather than passive collection.
        for pref_row in db.execute("SELECT id,privacy_json FROM users WHERE deleted_at IS NULL").fetchall():
            try: prefs=json.loads(pref_row["privacy_json"] or "{}")
            except Exception: prefs={}
            try: retention_days=max(1,min(3650,int(prefs.get("guestDataRetentionDays",365))))
            except Exception: retention_days=365
            cutoff=now-retention_days*24*60*60*1000
            owned=[r["id"] for r in db.execute("SELECT id FROM invitations WHERE owner_id=?",(pref_row["id"],)).fetchall()]
            for owned_id in owned:
                db.execute("DELETE FROM rsvps WHERE invitation_id=? AND created_at<?",(owned_id,cutoff))
                db.execute("DELETE FROM guest_messages WHERE invitation_id=? AND created_at<?",(owned_id,cutoff))
                db.execute("DELETE FROM view_events WHERE invitation_id=? AND viewed_at<?",(owned_id,cutoff))
        due=db.execute("SELECT id FROM users WHERE deletion_scheduled_at IS NOT NULL AND deletion_scheduled_at<=?",(now,)).fetchall()
        for user_row in due:
            user_id=user_row["id"];invites=db.execute("SELECT id FROM invitations WHERE owner_id=?",(user_id,)).fetchall()
            for invite in invites:
                rows=db.execute("SELECT object_id,path,sha256 FROM assets WHERE invitation_id=?",(invite["id"],)).fetchall()
                db.execute("DELETE FROM rsvps WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM guest_messages WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM view_events WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM access_tokens WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM gallery_access_tokens WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM publications WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM assets WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM guests WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM invitation_collaborators WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM invitation_comments WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM approval_requests WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM invitation_review_policies WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM review_notifications WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM review_tasks WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM invitation_studio_release_pins WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM upload_sessions WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM material_import_jobs WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM material_folders WHERE invitation_id=?",(invite["id"],));db.execute("DELETE FROM invitations WHERE id=?",(invite["id"],));purge.extend(release_stored_object_references(db,[r["object_id"] for r in rows]))
            roots=[row["id"] for row in db.execute("SELECT id FROM invitation_comments WHERE user_id=? AND parent_id=''",(user_id,)).fetchall()]
            for root_id in roots:db.execute("DELETE FROM invitation_comments WHERE id=? OR parent_id=?",(root_id,root_id))
            db.execute("DELETE FROM invitation_comments WHERE user_id=?",(user_id,));db.execute("DELETE FROM approval_requests WHERE requested_by=?",(user_id,));db.execute("UPDATE approval_requests SET decided_by='' WHERE decided_by=?",(user_id,));db.execute("DELETE FROM review_notifications WHERE user_id=? OR actor_id=?",(user_id,user_id));db.execute("UPDATE review_tasks SET assignee_id='' WHERE assignee_id=?",(user_id,));db.execute("UPDATE review_tasks SET updated_by='' WHERE updated_by=?",(user_id,));db.execute("UPDATE invitation_review_policies SET updated_by='' WHERE updated_by=?",(user_id,));db.execute("DELETE FROM invitation_collaborators WHERE user_id=?",(user_id,));db.execute("UPDATE invitation_studio_release_pins SET pinned_by='' WHERE pinned_by=?",(user_id,))
            backup_names=[Path(str(row["archive_name"] or "")).name for row in db.execute("SELECT archive_name FROM backup_runs WHERE owner_id=?",(user_id,)).fetchall()]
            for name in backup_names:
                if name:
                    try:(BACKUPS/name).unlink(missing_ok=True)
                    except OSError:pass
            for table in ("sessions","auth_tokens","passkeys","auth_challenges","user_templates","user_page_templates","user_components","studio_resources","studio_releases","studio_governance","studio_backup_policies","studio_bulk_jobs","backup_runs"):
                db.execute(f"DELETE FROM {table} WHERE user_id=?" if table in {"sessions","auth_tokens","passkeys","auth_challenges"} else f"DELETE FROM {table} WHERE owner_id=?",(user_id,))
            db.execute("UPDATE audit_events SET user_id=NULL WHERE user_id=?",(user_id,)) if DATABASE_KIND=="postgresql" else None
            db.execute("DELETE FROM users WHERE id=?",(user_id,));purged_users+=1
    queue_physical_deletions(purge)
    return {"sessions":int(sessions or 0),"authTokens":int(auth_tokens or 0),"accessTokens":int(access_tokens or 0),"galleryAccessTokens":int(gallery_access_tokens or 0),"challenges":int(challenges or 0),"purgedUsers":purged_users}


def validate_material_bytes(raw, mime):
    signatures = {
        "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
        "image/png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": lambda b: b.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP",
        "audio/mpeg": lambda b: b.startswith(b"ID3") or (len(b) >= 2 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0),
        "audio/mp4": lambda b: len(b) >= 12 and b[4:8] == b"ftyp",
        "video/mp4": lambda b: len(b) >= 12 and b[4:8] == b"ftyp",
        "video/webm": lambda b: b.startswith(b"\x1aE\xdf\xa3"),
        "font/woff2": lambda b: b.startswith(b"wOF2"),
    }
    check = signatures.get(mime)
    if not check or not check(raw): raise ValueError("Uploaded material content does not match its declared file type")
    return raw


def _font_name(font,name_ids,default=""):
    table=font.get("name")
    if not table:return default
    for name_id in name_ids:
        records=[record for record in table.names if int(record.nameID)==int(name_id)]
        records.sort(key=lambda record:(record.platformID not in (0,3),record.langID not in (0x409,0),record.platEncID))
        for record in records:
            try:value=record.toUnicode().strip()
            except Exception:continue
            value=re.sub(r"[\x00-\x1f\x7f]+"," ",value)
            value=re.sub(r"\s+"," ",value).strip()
            if value:return value[:120]
    return default


def _font_source_signature(raw):
    if raw.startswith(b"wOF2"):return "woff2"
    if raw.startswith(b"OTTO"):return "otf"
    if raw.startswith((b"\x00\x01\x00\x00",b"true",b"typ1")):return "ttf"
    if raw.startswith(b"ttcf"):raise ValueError("TrueType font collections are not supported. Upload one font face at a time.")
    raise ValueError("The selected file is not a valid TTF, OTF, or WOFF2 font.")


# Khmer text requires much more than a few Unicode code points. The core set
# below covers base letters, independent/dependent vowels, signs and COENG.
# Digits and historical symbols are reported separately but do not determine
# whether the font can safely become the invitation's primary Khmer face.
_KHMER_CORE_CODEPOINTS=frozenset(
    list(range(0x1780,0x17B4))+
    list(range(0x17B6,0x17D4))+
    [0x17DD]
)
_KHMER_BLOCK_CODEPOINTS=frozenset(list(range(0x1780,0x1800))+list(range(0x19E0,0x1A00)))
_KHMER_REQUIRED_FEATURES=frozenset({"pref","blwf","abvf","pstf","pres","blws","abvs","psts","abvm","blwm","dist"})


def _font_layout_metadata(font,table_tag):
    table=font.get(table_tag)
    if not table or not getattr(table,"table",None):return set(),set()
    scripts=set();features=set()
    try:scripts={str(record.ScriptTag).strip() for record in table.table.ScriptList.ScriptRecord}
    except Exception:pass
    try:features={str(record.FeatureTag).strip() for record in table.table.FeatureList.FeatureRecord}
    except Exception:pass
    return scripts,features


def _font_category(font,family=""):
    name=str(family or "").lower()
    if "sans" in name:return "sans"
    if "serif" in name:return "serif"
    os2=font.get("OS/2");panose=getattr(os2,"panose",None);serif=int(getattr(panose,"bSerifStyle",0) or 0)
    return "sans" if 11<=serif<=15 else "serif"


def _font_vertical_metrics(font,has_khmer=False):
    head=font.get("head");os2=font.get("OS/2");hhea=font.get("hhea")
    upm=max(16,int(getattr(head,"unitsPerEm",1000) or 1000))
    asc=max(int(getattr(os2,"sTypoAscender",0) or 0),int(getattr(hhea,"ascent",0) or 0),0)
    desc=max(abs(int(getattr(os2,"sTypoDescender",0) or 0)),abs(int(getattr(hhea,"descent",0) or 0)),0)
    gap=max(int(getattr(os2,"sTypoLineGap",0) or 0),int(getattr(hhea,"lineGap",0) or 0),0)
    ratio=(asc+desc+gap)/upm
    minimum=1.38 if has_khmer else 1.2
    recommended=max(minimum,min(1.8,ratio+0.06))
    return {
        "unitsPerEm":upm,
        "ascentRatio":round(asc/upm,4),
        "descentRatio":round(desc/upm,4),
        "lineGapRatio":round(gap/upm,4),
        "recommendedLineHeight":round(recommended,2),
    }


def _khmer_font_metadata(font,cmap):
    core_present=_KHMER_CORE_CODEPOINTS.intersection(cmap)
    block_present=_KHMER_BLOCK_CODEPOINTS.intersection(cmap)
    core_percent=round(len(core_present)/len(_KHMER_CORE_CODEPOINTS)*100,1)
    block_percent=round(len(block_present)/len(_KHMER_BLOCK_CODEPOINTS)*100,1)
    gsub_scripts,gsub_features=_font_layout_metadata(font,"GSUB")
    gpos_scripts,gpos_features=_font_layout_metadata(font,"GPOS")
    has_script="khmr" in gsub_scripts and "khmr" in gpos_scripts
    shaping_features=sorted(_KHMER_REQUIRED_FEATURES.intersection(gsub_features|gpos_features))
    has_shaping=has_script and bool(gsub_features.intersection({"pref","blwf","abvf","pstf"})) and bool(gpos_features.intersection({"abvm","blwm","dist"}))
    # Require near-complete modern Khmer coverage. A font that merely includes
    # digits or a few symbols remains usable for Latin but is never selected as
    # the primary Khmer face; the trusted Noto Khmer fallback stays active.
    ready=core_percent>=92 and has_shaping
    missing=sorted(_KHMER_CORE_CODEPOINTS-core_present)
    warnings=[]
    if block_present and core_percent<92:warnings.append("Khmer core glyph coverage is incomplete")
    if block_present and not has_script:warnings.append("Khmer OpenType script tables are missing")
    elif block_present and not has_shaping:warnings.append("Khmer mark and coeng shaping features are incomplete")
    return {
        "khmerReady":ready,
        "khmerSupport":"ready" if ready else "partial" if block_present else "none",
        "khmerCoreCoveragePercent":core_percent,
        "khmerBlockCoveragePercent":block_percent,
        "khmerCoreGlyphs":len(core_present),
        "khmerCoreRequired":len(_KHMER_CORE_CODEPOINTS),
        "khmerShaping":has_shaping,
        "khmerScriptTables":has_script,
        "khmerFeatures":shaping_features,
        "khmerMissingCore":[f"U+{cp:04X}" for cp in missing[:16]],
        "khmerWarnings":warnings,
    }


def optimize_custom_font(raw,filename="font.ttf",declared_mime="application/octet-stream"):
    """Validate one user font and normalize it to a compact WOFF2 payload."""
    if not raw:raise ValueError("The selected font is empty")
    if len(raw)>MAX_CUSTOM_FONT_SOURCE_BYTES:raise ValueError("Custom fonts must be 8 MB or smaller")
    if str(declared_mime or "application/octet-stream").lower() not in FONT_SOURCE_MIMES:
        raise ValueError("Unsupported custom font MIME type")
    source_format=_font_source_signature(raw)
    try:
        from fontTools.ttLib import TTFont,TTLibError
    except ImportError as exc:
        raise RuntimeError("Custom font optimization requires fonttools[woff]. Install requirements-test.txt or requirements-production.txt.") from exc
    try:
        font=TTFont(io.BytesIO(raw),lazy=False,recalcTimestamp=False,ignoreDecompileErrors=False)
    except Exception as exc:
        raise ValueError("The selected font could not be parsed safely") from exc
    try:
        tags=list(font.keys())
        if len(tags)>MAX_CUSTOM_FONT_TABLES:raise ValueError("The font contains too many internal tables")
        if "cmap" not in font or "name" not in font or "maxp" not in font:raise ValueError("The font is missing required OpenType tables")
        glyph_count=int(getattr(font["maxp"],"numGlyphs",0) or 0)
        if glyph_count<=0 or glyph_count>MAX_CUSTOM_FONT_GLYPHS:raise ValueError("The font glyph count is outside the supported range")
        # Browser-executable SVG glyph payloads are intentionally excluded from
        # uploaded fonts. Color bitmap/vector tables can be added in a later,
        # separately audited release.
        for unsafe in ("SVG ","EBDT","CBDT","sbix"):
            if unsafe in font:raise ValueError("Color or SVG glyph fonts are not supported in this release")
        cmap={int(codepoint) for table in font["cmap"].tables if getattr(table,"isUnicode",lambda:False)() for codepoint in table.cmap.keys()}
        if not cmap:raise ValueError("The font does not contain a usable Unicode character map")
        family=_font_name(font,(16,1),Path(str(filename or "font")).stem or "Custom Font")
        subfamily=_font_name(font,(17,2),"Regular")
        postscript=_font_name(font,(6,),re.sub(r"[^A-Za-z0-9-]+","-",family).strip("-") or "CustomFont")
        os2=font.get("OS/2");head=font.get("head")
        weight=max(100,min(900,int(getattr(os2,"usWeightClass",400) or 400)))
        italic=bool((int(getattr(os2,"fsSelection",0) or 0)&1) or (int(getattr(head,"macStyle",0) or 0)&2))
        khmer=_khmer_font_metadata(font,cmap)
        has_khmer=khmer["khmerSupport"]!="none"
        scripts=[]
        if has_khmer:scripts.append("Khmer")
        if any((0x0041<=cp<=0x024F) or (0x1E00<=cp<=0x1EFF) for cp in cmap):scripts.append("Latin")
        if not scripts:scripts.append("Unicode")
        metrics=_font_vertical_metrics(font,has_khmer)
        category=_font_category(font,family)
        # Strip signatures/vendor timestamps that do not affect rendering and
        # make otherwise identical uploads hash differently.
        for tag in ("DSIG","FFTM"):
            if tag in font:del font[tag]
        font.flavor="woff2"
        out=io.BytesIO();font.save(out,reorderTables=True);optimized=out.getvalue()
        if not optimized.startswith(b"wOF2"):raise ValueError("The font could not be normalized to WOFF2")
        # A valid source WOFF2 can occasionally already be smaller than a fresh
        # serialization. Preserve the smaller representation after validation.
        if source_format=="woff2" and len(raw)<=len(optimized):optimized=raw
        return optimized,{
            "family":family,"subfamily":subfamily,"postscriptName":postscript,
            "weight":weight,"style":"italic" if italic else "normal","scripts":scripts,
            "category":category,"glyphCount":glyph_count,"sourceFormat":source_format,"format":"woff2",
            "optimizationProfile":"khmer-safe-full","originalBytes":len(raw),"optimizedBytes":len(optimized),
            "savingsPercent":max(0,round((1-len(optimized)/max(1,len(raw)))*100,1)),
            **metrics,**khmer,
        }
    finally:
        try:font.close()
        except Exception:pass

def clean_slug(value):
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return value[:60] or "our-invitation"

def guest_token_value(guest_id, token_salt, token_version=1):
    payload=f"{guest_id}|{token_salt}|{int(token_version or 1)}"
    digest=hmac.new(GUEST_TOKEN_SECRET.encode(),payload.encode(),hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")[:32]

def guest_token_hash(token):
    return hashlib.sha256(str(token or "").encode()).hexdigest()

def redact_request_path(value):
    """Redact credentials and personalized guest tokens from request logs."""
    raw = str(value or "")
    return re.sub(r"([?&](?:access|guest|g|token|code)=)[^&]*", r"\1[redacted]", raw, flags=re.I)

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),210_000).hex()


def enqueue_background_job(kind,payload,delay_ms=0):
    now=int(time.time()*1000);job_id=str(uuid.uuid4())
    with connect() as db:db.execute("INSERT INTO background_jobs(id,kind,payload_json,state,attempts,available_at,created_at,updated_at) VALUES(?,?,?,'queued',0,?,?,?)",(job_id,str(kind),json.dumps(payload,ensure_ascii=False),now+max(0,int(delay_ms)),now,now))
    return job_id

def claim_background_job(kinds=None):
    now=int(time.time()*1000)
    with connect() as db:
        params=[now];where="state='queued' AND available_at<=?"
        if kinds:
            marks=','.join('?' for _ in kinds);where+=f" AND kind IN ({marks})";params.extend(kinds)
        row=db.execute(f"SELECT * FROM background_jobs WHERE {where} ORDER BY created_at LIMIT 1",tuple(params)).fetchone()
        if not row:return None
        changed=db.execute("UPDATE background_jobs SET state='running',locked_at=?,attempts=attempts+1,updated_at=? WHERE id=? AND state='queued'",(now,now,row["id"])).rowcount
        if not changed:return None
        result=dict(row);result["payload"]=json.loads(result.pop("payload_json") or "{}");return result

def complete_background_job(job_id):
    with connect() as db:db.execute("UPDATE background_jobs SET state='done',locked_at=NULL,updated_at=? WHERE id=?",(int(time.time()*1000),job_id))

def fail_background_job(job_id,error,retry=True):
    now=int(time.time()*1000)
    with connect() as db:
        row=db.execute("SELECT attempts FROM background_jobs WHERE id=?",(job_id,)).fetchone();attempts=int(row["attempts"] or 0) if row else 0
        state='queued' if retry and attempts<5 else 'failed';delay=min(60_000*(2**max(0,attempts-1)),3_600_000)
        db.execute("UPDATE background_jobs SET state=?,available_at=?,locked_at=NULL,last_error=?,updated_at=? WHERE id=?",(state,now+delay,str(error)[:2000],now,job_id))

def schedule_media_derivatives(path,mime,sha256):
    if not str(mime).startswith('image/'):return None
    if BACKGROUND_MEDIA_ENABLED:return enqueue_background_job('image.derivatives',{'path':path,'mime':mime,'sha256':sha256})
    pre_generate_common_derivatives(path,mime,sha256);return None

def schedule_social_warm(invite_id,access_mode,version,document):
    if BACKGROUND_MEDIA_ENABLED:return enqueue_background_job('social.warm',{'invitationId':invite_id,'accessMode':access_mode,'version':version,'document':document})
    warm_social_card_cache(invite_id,access_mode,version,document);return None

def record_bandwidth_for_path(path,byte_count):
    clean=Path(str(path or '')).name
    try:
        with connect() as db:
            row=db.execute("SELECT owner_id FROM stored_objects WHERE path=?",(clean,)).fetchone()
            if row:db.execute("INSERT INTO bandwidth_events(id,owner_id,bytes,created_at) VALUES(?,?,?,?)",(str(uuid.uuid4()),row['owner_id'],max(0,int(byte_count)),int(time.time()*1000)))
    except Exception:pass

def bandwidth_usage_30d(owner_id,db=None):
    cutoff=int(time.time()*1000)-BANDWIDTH_WINDOW_MS
    if db is not None:
        row=db.execute("SELECT COALESCE(SUM(bytes),0) total FROM bandwidth_events WHERE owner_id=? AND created_at>=?",(owner_id,cutoff)).fetchone()
        return int(row['total'] or 0)
    with connect() as conn:
        row=conn.execute("SELECT COALESCE(SUM(bytes),0) total FROM bandwidth_events WHERE owner_id=? AND created_at>=?",(owner_id,cutoff)).fetchone()
    return int(row['total'] or 0)


def bandwidth_delivery_allowed(path,pending_bytes=0):
    """Apply plan bandwidth limits to media delivery when enforcement is enabled."""
    if not PLAN_LIMITS_ENFORCED:return True,None
    clean=Path(str(path or '')).name
    if not clean:return False,None
    with connect() as db:
        row=db.execute("SELECT so.owner_id,u.plan FROM stored_objects so JOIN users u ON u.id=so.owner_id WHERE so.path=? LIMIT 1",(clean,)).fetchone()
        if not row:return True,None
        plan=normalize_plan(row['plan']);limit=int(PLAN_LIMITS.get(plan,PLAN_LIMITS['free']).get('bandwidthBytes30d') or 0)
        used=bandwidth_usage_30d(row['owner_id'],db)
    return used+max(0,int(pending_bytes))<=limit,{"ownerId":row['owner_id'],"plan":plan,"used":used,"limit":limit}


def process_scheduled_publications():
    now=int(time.time()*1000);changed={"published":0,"unpublished":0,"expired":0}
    with connect() as db:
        changed["published"]=db.execute("UPDATE invitations SET is_published=1,publish_at=NULL,updated_at=? WHERE deleted_at IS NULL AND publish_at IS NOT NULL AND publish_at<=? AND EXISTS(SELECT 1 FROM publications p WHERE p.invitation_id=invitations.id)",(now,now)).rowcount
        changed["unpublished"]=db.execute("UPDATE invitations SET is_published=0,unpublish_at=NULL,updated_at=? WHERE unpublish_at IS NOT NULL AND unpublish_at<=?",(now,now)).rowcount
        changed["expired"]=db.execute("UPDATE invitations SET is_published=0,updated_at=? WHERE expires_at IS NOT NULL AND expires_at<=? AND is_published=1",(now,now)).rowcount
    return changed

def valid_custom_domain(value):
    host=str(value or '').strip().lower().rstrip('.')
    if not host:return ''
    if len(host)>253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',host):raise ValueError('Invalid custom domain')
    if CUSTOM_DOMAIN_SUFFIX_ALLOWLIST and not any(host==suffix or host.endswith('.'+suffix) for suffix in CUSTOM_DOMAIN_SUFFIX_ALLOWLIST):raise ValueError('This custom domain is not allowed by the deployment configuration')
    return host

def send_message_provider(channel,recipient,message,metadata=None):
    channel=str(channel or '').lower();recipient=str(recipient or '').strip();message=str(message or '')[:5000];metadata=metadata or {}
    if channel=='email':
        if not recipient or '@' not in recipient:return {"status":"skipped","error":"Guest email is missing"}
        try:return {"status":"sent" if send_platform_email(recipient,metadata.get('subject') or 'You are invited',message) else "queued","providerId":"smtp"}
        except Exception as exc:return {"status":"failed","error":str(exc)}
    if channel not in {'sms','whatsapp','telegram'}:return {"status":"failed","error":"Unsupported messaging channel"}
    if not MESSAGING_WEBHOOK_ENDPOINT:return {"status":"preview","error":"Messaging provider is not configured"}
    payload=json.dumps({"channel":channel,"recipient":recipient,"message":message,"metadata":metadata}).encode('utf-8');headers={"Content-Type":"application/json"}
    if MESSAGING_WEBHOOK_SECRET:headers['Authorization']='Bearer '+MESSAGING_WEBHOOK_SECRET
    try:
        req=urllib.request.Request(MESSAGING_WEBHOOK_ENDPOINT,data=payload,headers=headers,method='POST')
        with urllib.request.urlopen(req,timeout=12) as response:
            body=json.loads(response.read() or b'{}');return {"status":"sent","providerId":str(body.get('id','webhook'))}
    except Exception as exc:return {"status":"failed","error":str(exc)}

def process_scheduled_campaigns():
    now=int(time.time()*1000)
    with connect() as db:
        campaigns=[dict(r) for r in db.execute("SELECT * FROM message_campaigns WHERE state='scheduled' AND scheduled_at IS NOT NULL AND scheduled_at<=? ORDER BY scheduled_at LIMIT 20",(now,)).fetchall()]
    processed=0
    for campaign in campaigns:
        try:
            segment=json.loads(campaign.get('segment_json') or '{}')
            with connect() as db:rows=[dict(r) for r in db.execute("SELECT * FROM guests WHERE invitation_id=?",(campaign['invitation_id'],)).fetchall()]
            guests=[]
            for guest in rows:
                try:tags=json.loads(guest.get('tags_json') or '[]')
                except Exception:tags=[]
                if segment.get('group') and guest.get('group_name')!=segment['group']:continue
                if segment.get('tag') and segment['tag'] not in tags:continue
                guests.append(guest)
            sent=preview=failed=0
            with connect() as db:
                for guest in guests:
                    recipient=guest.get('email') if campaign['channel']=='email' else guest.get('phone')
                    result=send_message_provider(campaign['channel'],recipient,campaign['message'],{'guestName':guest.get('name'),'invitationId':campaign['invitation_id']})
                    state=result.get('status','failed');sent+=state=='sent';preview+=state in {'preview','queued'};failed+=state in {'failed','skipped'};stamp=int(time.time()*1000)
                    db.execute("INSERT INTO message_deliveries(id,campaign_id,guest_id,channel,status,provider_id,error,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(str(uuid.uuid4()),campaign['id'],guest['id'],campaign['channel'],state,result.get('providerId',''),result.get('error',''),stamp,stamp))
                    if state=='sent':db.execute("UPDATE guests SET delivery_status='sent' WHERE id=?",(guest['id'],))
                db.execute("UPDATE message_campaigns SET state=?,updated_at=? WHERE id=?",('sent' if failed==0 else 'partial',int(time.time()*1000),campaign['id']))
            processed+=1
        except Exception as exc:
            with connect() as db:db.execute("UPDATE message_campaigns SET state='failed',updated_at=? WHERE id=?",(int(time.time()*1000),campaign['id']))
    return processed

def studio_print_fingerprint(document):
    payload={key:document.get(key) for key in ("schemaVersion","fields","canvasFormat","templateFamily","eventBrand","typography","objects","designPages","masterPageStyle","palette","accent")}
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def studio_document_resource_references(document):
    refs={}
    governance=document.get("studioGovernance") if isinstance(document.get("studioGovernance"),dict) else {}
    def add(resource_id,version=0,kind=""):
        resource_id=str(resource_id or "").strip()
        if not resource_id or resource_id in refs:return
        try:version=int(version or 0)
        except (TypeError,ValueError):version=0
        refs[resource_id]={"id":resource_id,"version":max(0,version),"kind":str(kind or "").strip()}
    brand_id=governance.get("brandResourceId") or (governance.get("resourceId") if governance.get("resourceKind")=="brand" else "") or ((document.get("eventBrand") or {}).get("id") if isinstance(document.get("eventBrand"),dict) and (document.get("eventBrand") or {}).get("governed") else "")
    add(brand_id,governance.get("brandResourceVersion") or governance.get("resourceVersion"),"brand")
    family=document.get("templateFamily") if isinstance(document.get("templateFamily"),dict) else {}
    add(family.get("resourceId"),family.get("resourceVersion"),"template-family")
    maps=[document.get("objects") or {}]+[(page.get("objects") or {}) for page in (document.get("designPages") or []) if isinstance(page,dict)]
    for object_map in maps:
        if not isinstance(object_map,dict):continue
        for obj in object_map.values():
            if isinstance(obj,dict):add(obj.get("studioResourceId"),obj.get("studioResourceVersion"),"component")
    for ref in (governance.get("appliedResources") or {}).values() if isinstance(governance.get("appliedResources"),dict) else []:
        if isinstance(ref,dict):add(ref.get("id"),ref.get("version"),ref.get("kind"))
    return list(refs.values())

def studio_brand_lock_blockers(document,resource_row,policy):
    blockers=[]
    try:payload=json.loads(resource_row["payload_json"] or "{}")
    except Exception:payload={}
    try:resource_governance=json.loads(resource_row["governance_json"] or "{}")
    except Exception:resource_governance={}
    if resource_row["kind"]!="brand" or not resource_governance.get("locked"):return blockers
    palette=document.get("palette") if isinstance(document.get("palette"),dict) else {}
    def same(a,b):return str(a or "").strip().lower()==str(b or "").strip().lower()
    if policy.get("lockBrandColors"):
        expected={"background":payload.get("background"),"surface":payload.get("surface"),"text":payload.get("text"),"heading":payload.get("primary")}
        color_mismatch=any(value and not same(palette.get(key),value) for key,value in expected.items())
        if payload.get("accent") and not same(document.get("accent"),payload.get("accent")):color_mismatch=True
        if color_mismatch:blockers.append({"code":"brand_colors_locked","message":"Restore the approved studio brand colors before publishing."})
    if policy.get("lockTypography"):
        styles=((document.get("typography") or {}).get("styles") or {}) if isinstance(document.get("typography"),dict) else {}
        heading_pair=str(payload.get("headingPair") or "").strip();body_pair=str(payload.get("bodyPair") or "").strip();mismatch=False
        if heading_pair:
            targets=[styles.get(key) for key in ("display","heading","subheading","khmer-ceremonial") if isinstance(styles.get(key),dict)]
            mismatch=mismatch or not targets or any(str(style.get("fontPairing") or "")!=heading_pair for style in targets)
        if body_pair:
            targets=[styles.get(key) for key in ("body","caption") if isinstance(styles.get(key),dict)]
            mismatch=mismatch or not targets or any(str(style.get("fontPairing") or "")!=body_pair for style in targets)
        if mismatch:blockers.append({"code":"brand_typography_locked","message":"Restore the approved studio typography pairings before publishing."})
    return blockers

def studio_publish_readiness(db, owner_id, document, invitation_id=""):
    row=db.execute("SELECT policy_json FROM studio_governance WHERE owner_id=?",(owner_id,)).fetchone()
    if not row:return {"ready":True,"policy":{},"blockers":[]}
    try:policy=json.loads(row["policy_json"] or "{}")
    except Exception:policy={}
    blockers=[]
    if policy.get("requireAdaptiveTemplate") and not bool((document.get("templateFamily") or {}).get("adaptive")):
        blockers.append({"code":"adaptive_template_required","message":"Apply an adaptive studio template family before publishing."})
    refs=studio_document_resource_references(document);resolved={}
    for ref in refs:
        resource=db.execute("SELECT id,kind,status,version,payload_json,governance_json FROM studio_resources WHERE id=? AND owner_id=?",(ref["id"],owner_id)).fetchone()
        if resource:resolved[ref["id"]]=resource
        if policy.get("approvedOnly"):
            if not resource:blockers.append({"code":"approved_resource_unavailable","message":"A governed studio resource is missing or belongs to another studio."})
            elif resource["status"]!="approved":blockers.append({"code":"approved_resource_required","message":f"{resource['kind'].replace('-',' ').title()} resource is not approved for official use."})
            elif ref["version"] and int(resource["version"] or 1)!=ref["version"]:blockers.append({"code":"governed_resource_outdated","message":"Apply the current approved studio-resource version before publishing."})
    if policy.get("approvedOnly") and not refs:
        blockers.append({"code":"approved_resource_required","message":"Studio policy requires at least one approved governed resource."})
    governance=document.get("studioGovernance") if isinstance(document.get("studioGovernance"),dict) else {}
    brand_id=governance.get("brandResourceId") or (governance.get("resourceId") if governance.get("resourceKind")=="brand" else "") or ((document.get("eventBrand") or {}).get("id") if isinstance(document.get("eventBrand"),dict) and (document.get("eventBrand") or {}).get("governed") else "")
    if brand_id and brand_id in resolved:blockers.extend(studio_brand_lock_blockers(document,resolved[brand_id],policy))
    if policy.get("requirePrintPreflight"):
        preflight=document.get("printReadiness") if isinstance(document.get("printReadiness"),dict) else {}
        expected=studio_print_fingerprint(document)
        if preflight.get("status")!="ready":blockers.append({"code":"print_preflight_required","message":"Run and mark the print preflight current before publishing."})
        elif preflight.get("fingerprint")!=expected:blockers.append({"code":"print_preflight_stale","message":"The invitation changed after its last print preflight."})
    if policy.get("requireStudioRelease"):
        pin=db.execute("SELECT release_id,release_version FROM invitation_studio_release_pins WHERE invitation_id=? AND owner_id=?",(invitation_id,owner_id)).fetchone() if invitation_id else None
        if not pin:blockers.append({"code":"studio_release_required","message":"Pin this invitation to the active studio release before publishing."})
        else:
            release=db.execute("SELECT id,status,version,manifest_json FROM studio_releases WHERE id=? AND owner_id=?",(pin["release_id"],owner_id)).fetchone()
            if not release or release["status"]!="active":blockers.append({"code":"studio_release_inactive","message":"The pinned studio release is no longer active."})
            elif int(release["version"] or 1)!=int(pin["release_version"] or 1):blockers.append({"code":"studio_release_pin_outdated","message":"Re-pin this invitation to the current studio release version."})
            else:
                try:manifest=json.loads(release["manifest_json"] or "[]")
                except Exception:manifest=[]
                manifest_map={str(item.get("id","")):(int(item.get("version") or 1),str(item.get("kind",""))) for item in manifest if isinstance(item,dict) and item.get("id")}
                if not manifest_map:blockers.append({"code":"studio_release_empty","message":"The active studio release does not contain approved resources."})
                for resource_id,(release_version,release_kind) in manifest_map.items():
                    live=db.execute("SELECT kind,status,version FROM studio_resources WHERE id=? AND owner_id=?",(resource_id,owner_id)).fetchone()
                    if not live:blockers.append({"code":"studio_release_resource_missing","message":"A resource included in the active studio release is no longer available."})
                    elif live["status"]!="approved" or str(live["kind"])!=release_kind or int(live["version"] or 1)!=release_version:blockers.append({"code":"studio_release_resource_changed","message":"The active studio release contains a resource that changed after activation. Activate a new release."})
                for ref in refs:
                    expected_ref=manifest_map.get(ref["id"])
                    if not expected_ref:blockers.append({"code":"studio_release_resource_unpinned","message":"A governed resource used by this invitation is outside the pinned studio release."})
                    elif ref["version"] and expected_ref[0]!=ref["version"]:blockers.append({"code":"studio_release_resource_outdated","message":"Apply the resource versions included in the pinned studio release."})
    unique=[];seen=set()
    for blocker in blockers:
        key=(blocker.get("code"),blocker.get("message"))
        if key not in seen:seen.add(key);unique.append(blocker)
    return {"ready":not unique,"policy":{k:bool(policy.get(k,False)) for k in ("approvedOnly","lockBrandColors","lockTypography","requireAdaptiveTemplate","requirePrintPreflight","requireStudioRelease")},"blockers":unique}


def safe_request_id(value):
    """Normalize correlation IDs before reflecting them into logs or headers."""
    clean=re.sub(r"[^A-Za-z0-9._:-]","",str(value or ""))[:80]
    return clean or uuid.uuid4().hex


def is_loopback_address(value):
    try:return ipaddress.ip_address(str(value or "").split("%",1)[0]).is_loopback
    except ValueError:return str(value or "").lower() in {"localhost","ip6-localhost"}


class Handler(SimpleHTTPRequestHandler):
    server_version="EInvite"
    sys_version=""
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT), **kwargs)
    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_SOCKET_TIMEOUT_SECONDS)
    def log_message(self, format, *args):
        # Keep request handling independent from a terminal that may be closed.
        if JSON_LOGS:
            try:
                print(json.dumps({"ts":int(time.time()*1000),"client":self.client_address[0],"method":getattr(self,"command",None),"path":redact_request_path(getattr(self,"path",None)),"message":redact_request_path(format%args)},ensure_ascii=False),flush=True)
            except Exception:pass
    def end_headers(self):
        request_id=safe_request_id(getattr(self,"request_id",None) or self.headers.get("X-Request-ID"))
        self.request_id=request_id
        self.send_header("X-Request-ID",request_id)
        if getattr(self,"_expire_stale_session",False) and not getattr(self,"_session_replaced",False):
            stale=f"{SESSION_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
            csrf="einvite_csrf=; Path=/; Max-Age=0; SameSite=Lax"
            if COOKIE_SECURE:stale+="; Secure";csrf+="; Secure"
            self.send_header("Set-Cookie",stale);self.send_header("Set-Cookie",csrf)
            self._expire_stale_session=False
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(self), microphone=(), geolocation=()" if "/checkin" in urlparse(getattr(self,"path","")).path else "camera=(), microphone=(), geolocation=()")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-site")
        if COOKIE_SECURE:self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; style-src 'self'; style-src-elem 'self'; style-src-attr 'unsafe-inline'; img-src 'self' data: blob: https:; media-src 'self' data: blob: https:; font-src 'self' data: https:; frame-src https://www.youtube.com https://www.youtube-nocookie.com https://w.soundcloud.com; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'")
        super().end_headers()
    def safe_write(self, body):
        try:
            self.wfile.write(body)
            return True
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            return False
    def json(self, status, value, headers=None):
        body = json.dumps(value, ensure_ascii=False).encode()
        response_headers={"Cache-Control":"no-store",**(headers or {})}
        try:
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body)))
            for key,val in response_headers.items():
                if isinstance(val,(list,tuple)):
                    for item in val:self.send_header(key,str(item))
                else:self.send_header(key,str(val))
            self.end_headers()
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            return False
        return self.safe_write(body)
    def request_authority(self):
        """Return a normalized HTTP authority or an empty string when malformed."""
        value=(self.headers.get("Host") or "").strip().lower()
        if not value or any(ord(ch)<0x21 or ord(ch)>0x7e for ch in value) or any(ch in value for ch in "/\\@?#"):
            return ""
        if value.startswith("["):
            match=re.fullmatch(r"\[([0-9a-f:.]+)\](?::([0-9]{1,5}))?",value)
            if not match:return ""
            try:
                address=ipaddress.ip_address(match.group(1))
                if address.version!=6:return ""
            except ValueError:return ""
            port=match.group(2)
            if port and not 1<=int(port)<=65535:return ""
            return f"[{address.compressed}]"+(f":{port}" if port else "")
        if value.count(":")>1:return ""
        host,separator,port=value.rpartition(":")
        if not separator:host=value;port=""
        elif not port.isdigit() or not 1<=int(port)<=65535:return ""
        host=host.rstrip(".")
        if not host:return ""
        try:ipaddress.ip_address(host)
        except ValueError:
            label=r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            if host!="localhost" and not re.fullmatch(rf"{label}(?:\.{label})*",host):return ""
        return host+(f":{port}" if port else "")
    def request_host(self):
        authority=self.request_authority()
        if authority.startswith("["):return authority[1:authority.find("]")]
        return authority.rsplit(":",1)[0] if authority.count(":")==1 else authority
    def guard_request_boundary(self):
        """Reject ambiguous request framing and untrusted Host headers."""
        transfer=(self.headers.get("Transfer-Encoding") or "").strip().lower()
        lengths=self.headers.get_all("Content-Length") or []
        if transfer and transfer!="identity":
            self.json(400,{"error":"Unsupported request transfer encoding","code":"request_framing_rejected"});return False
        if len(lengths)>1:
            self.json(400,{"error":"Ambiguous request length","code":"request_framing_rejected"});return False
        authority=self.request_authority();host=self.request_host()
        if self.request_version=="HTTP/1.1" and not authority:
            self.json(400,{"error":"A valid Host header is required","code":"host_required"});return False
        if ALLOWED_HOSTS and host not in ALLOWED_HOSTS:
            allowed_custom=False
            if host:
                try:
                    with connect() as db:
                        allowed_custom=db.execute("SELECT 1 FROM invitations WHERE custom_domain=? AND is_published=1 AND archived=0 AND deleted_at IS NULL LIMIT 1",(host,)).fetchone() is not None
                except Exception:allowed_custom=False
            if not allowed_custom:
                self.json(421,{"error":"The requested host is not configured","code":"host_rejected"});return False
        ai_token=(self.headers.get("X-EInvite-AI-Authorization") or "").strip()
        if ai_token:
            user=self.user();invitation_id=(self.headers.get("X-EInvite-AI-Invitation") or "").strip()[:120];tool_id=(self.headers.get("X-EInvite-AI-Tool-Id") or "").strip()[:120]
            if not user:
                self.json(401,{"error":"Authentication required","code":"authentication_required"});return False
            try:get_ai_agent_service().consume_tool_authorization(ai_token,invitation_id,user["id"],tool_id,self.command,urlsplit(self.path).path)
            except AgentServiceError as exc:
                self.json(exc.status,exc.payload());return False
        return True
    def guard_cookie_origin(self, require_session_csrf=True):
        """Enforce same-origin browser mutations and session-bound CSRF separately.

        Authentication bootstrap endpoints still enforce Origin/Sec-Fetch-Site, but
        deliberately ignore stale session CSRF material so an invalid localhost
        cookie cannot lock the user out of registration or login.
        """
        origin=(self.headers.get("Origin") or "").strip();fetch_site=(self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        host=self.request_authority();allowed={f"http://{host}",f"https://{host}"}
        if PUBLIC_BASE_URL:
            try:
                parsed=urlparse(PUBLIC_BASE_URL);allowed.add(f"{parsed.scheme}://{parsed.netloc}")
            except Exception:pass
        if fetch_site in {"cross-site","same-site"}:
            self.json(403,{"error":"Cross-site request rejected","code":"csrf_rejected"});return False
        if origin and origin.rstrip("/") not in {x.rstrip("/") for x in allowed if x}:
            self.json(403,{"error":"Cross-site request rejected","code":"csrf_rejected"});return False

        session_token=self.cookie_token();valid_session=False
        if session_token:
            token_hash=hashlib.sha256(session_token.encode()).hexdigest();now=int(time.time()*1000)
            with connect() as db:
                valid_session=db.execute("SELECT 1 FROM sessions WHERE token_hash=? AND expires_at>?",(token_hash,now)).fetchone() is not None
            if not valid_session:
                self._expire_stale_session=True
                session_token=None

        # Only an authenticated browser session needs the double-submit token.
        if require_session_csrf and valid_session and (STRICT_SESSION_CSRF or origin or fetch_site):
            header=(self.headers.get("X-CSRF-Token") or "").strip();cookie_value=""
            try:
                cookie=SimpleCookie();cookie.load(self.headers.get("Cookie", ""));m=cookie.get("einvite_csrf");cookie_value=m.value if m else ""
            except Exception:pass
            if not header or not cookie_value or not hmac.compare_digest(header,cookie_value):
                self.json(403,{"error":"Missing or invalid CSRF token","code":"csrf_required"});return False
            token_hash=hashlib.sha256(session_token.encode()).hexdigest();csrf_hash=hashlib.sha256(header.encode()).hexdigest()
            with connect() as db:
                row=db.execute("SELECT 1 FROM sessions WHERE token_hash=? AND csrf_hash=? AND expires_at>?",(token_hash,csrf_hash,int(time.time()*1000))).fetchone()
            if not row:
                self.json(403,{"error":"CSRF token does not match this session","code":"csrf_invalid"});return False
        return True

    def body(self, limit=20_000_000):
        try:size=int(self.headers.get("Content-Length", "0"))
        except (TypeError,ValueError):raise ValueError("Invalid request length")
        if size<0:raise ValueError("Invalid request length")
        if size > limit: raise ValueError("Request too large")
        return json.loads(self.rfile.read(size) or b"{}")
    def mutation_identity(self):
        def clean(value):
            return re.sub(r"[^A-Za-z0-9._:-]", "", str(value or ""))[:120]
        return clean(self.headers.get("X-EInvite-Client-Id")), clean(self.headers.get("X-EInvite-Mutation-Id"))
    def bearer_token(self):
        header=self.headers.get("Authorization","")
        return header[7:].strip() if header.startswith("Bearer ") else None
    def cookie_token(self):
        raw_cookie=self.headers.get("Cookie","")
        if raw_cookie:
            try:
                cookie=SimpleCookie();cookie.load(raw_cookie);morsel=cookie.get(SESSION_COOKIE_NAME)
                if morsel and morsel.value:return morsel.value
            except Exception:pass
        return None
    def auth_tokens(self):
        values=[]
        # Production browser authentication is cookie-only. Bearer sessions exist solely for
        # explicit automated-development compatibility and are disabled by default.
        candidates=[self.cookie_token()]
        if DEV_AUTH_TOKENS_ENABLED:candidates.append(self.bearer_token())
        for value in candidates:
            if value and value not in values:values.append(value)
        return values
    def auth_token(self):
        tokens=self.auth_tokens()
        return tokens[0] if tokens else None
    def user(self):
        tokens=self.auth_tokens()
        if not tokens:return None
        now=int(time.time()*1000)
        with connect() as db:
            for token in tokens:
                token_hash=hashlib.sha256(token.encode()).hexdigest()
                row=db.execute("SELECT u.id,u.email,u.role,u.email_verified,u.plan,u.upload_enabled,u.mfa_enabled,u.deleted_at,s.created_at session_created_at,s.last_seen_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.deleted_at IS NULL",(token_hash,now)).fetchone()
                if row:
                    try:db.execute("UPDATE sessions SET last_seen_at=? WHERE token_hash=? AND last_seen_at<?",(now,token_hash,now-60_000))
                    except Exception:pass
                    return row
        if self.cookie_token():self._expire_stale_session=True
        return None
    def require_user(self):
        user=self.user()
        if not user:self.json(401,{"error":"Authentication required"})
        return user
    def require_upload_permission(self,user):
        enabled=bool(user["upload_enabled"] if user is not None and "upload_enabled" in user.keys() else 1)
        if not enabled:
            self.json(403,{"error":"Uploads are disabled for this account","code":"upload_disabled"});return False
        return True
    def require_role(self,*roles):
        user=self.require_user()
        if not user:return None
        if user["role"] not in roles:self.json(403,{"error":"Insufficient permissions"});return None
        return user
    def owns(self, db, invite_id, user_id):
        return db.execute("SELECT 1 FROM invitations WHERE id=? AND owner_id=? AND deleted_at IS NULL",(invite_id,user_id)).fetchone() is not None
    def invitation_role(self, db, invite_id, user_id):
        if self.owns(db,invite_id,user_id):return "owner"
        row=db.execute("SELECT role FROM invitation_collaborators WHERE invitation_id=? AND user_id=?",(invite_id,user_id)).fetchone()
        return row["role"] if row else None
    def can_read_invitation(self, db, invite_id, user_id):
        return self.invitation_role(db,invite_id,user_id) is not None
    def can_edit_invitation(self, db, invite_id, user_id):
        return self.invitation_role(db,invite_id,user_id) in {"owner","content","designer","manager"}
    def can_manage_invitation(self, db, invite_id, user_id):
        return self.invitation_role(db,invite_id,user_id) in {"owner","manager"}
    def invitation_owner_user(self, db, invite_id):
        return db.execute("SELECT u.id,u.email,u.role,u.email_verified,u.plan FROM invitations i JOIN users u ON u.id=i.owner_id WHERE i.id=?",(invite_id,)).fetchone()
    def client_ip(self):
        direct=str(self.client_address[0] if self.client_address else "")
        if direct in TRUSTED_PROXY_IPS:
            forwarded=(self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            if forwarded:return forwarded[:80]
        return direct[:80]
    def origin_base(self):
        if PUBLIC_BASE_URL:return PUBLIC_BASE_URL.rstrip("/")
        scheme="https" if COOKIE_SECURE else "http"
        return f"{scheme}://{self.request_authority() or 'localhost'}"
    def rp_id(self):
        try:return urlparse(self.origin_base()).hostname or "localhost"
        except Exception:return "localhost"
    def audit(self, action, target_type="", target_id="", metadata=None, user_id=None):
        try:
            uid=user_id
            if uid is None:
                current=self.user();uid=current["id"] if current else None
            write_audit_event(uid,action,target_type,target_id,metadata,self.client_ip())
        except Exception as exc:
            if JSON_LOGS:print(json.dumps({"level":"warning","event":"audit_write_failed","message":str(exc)}),flush=True)
    def bot_protection_ok(self, action, token=""):
        if not BOT_PROTECTION_ENDPOINT:return True
        if not token:return False
        payload=json.dumps({"token":str(token)[:4000],"action":action,"ip":self.client_ip()}).encode()
        headers={"Content-Type":"application/json","User-Agent":"E-invitation-website/1.0"}
        if BOT_PROTECTION_SECRET:headers["Authorization"]=f"Bearer {BOT_PROTECTION_SECRET}"
        try:
            req=urllib.request.Request(BOT_PROTECTION_ENDPOINT,data=payload,headers=headers,method="POST")
            with urllib.request.urlopen(req,timeout=5) as response:result=json.loads(response.read(100000) or b"{}")
            return bool(result.get("success") or result.get("ok"))
        except Exception:return False
    def require_verified_for_sensitive_action(self, user, action="this action"):
        if user and not bool(user["email_verified"]):
            self.json(403,{"error":f"Verify your email before {action}","code":"email_verification_required"});return False
        return True
    def rate_limit(self, key, limit, window_seconds):
        bucket_key=str(key)
        client=redis_client()
        if client:
            try:
                redis_key=f"einvite:rate:{bucket_key}:{int(time.time()//window_seconds)}"
                count=client.incr(redis_key)
                if count==1:client.expire(redis_key,window_seconds+2)
                if count>limit:
                    self.json(429,{"error":"Too many requests. Please wait and try again."});return False
                return True
            except Exception:pass
        now=time.time()
        with RATE_LOCK:
            values=[stamp for stamp in RATE_BUCKETS.get(bucket_key,[]) if now-stamp<window_seconds]
            if len(values)>=limit:
                RATE_BUCKETS[bucket_key]=values
                self.json(429,{"error":"Too many requests. Please wait and try again."})
                return False
            values.append(now); RATE_BUCKETS[bucket_key]=values
        return True
    def serve_html_file(self, filename):
        path=(ROOT/filename).resolve()
        if path.parent!=ROOT or not path.is_file():return self.json(404,{"error":"Page not found"})
        page=path.read_text(encoding="utf-8")
        marker='<meta name="einvite-backend" content="full">'
        base='<base href="/">'
        head_bits=(marker if marker not in page else '')+(base if '<base ' not in page else '')
        if head_bits:
            page=page.replace('<head>',f'<head>{head_bits}',1)
        body=page.encode("utf-8")
        self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-cache");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

    def serve_management_page(self, invitation_id, section):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invitation_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        filename={"editor":"index.html","guests":"guests.html","responses":"responses.html","analytics":"analytics.html","materials":"materials.html","checkin":"checkin.html"}.get(section)
        if not filename:return self.json(404,{"error":"Management page not found"})
        return self.serve_html_file(filename)

    def public_static_path(self, request_path=None):
        """Resolve only browser assets that are intentionally public.

        SimpleHTTPRequestHandler otherwise exposes every file beneath ROOT,
        including databases, backups, environment files, source code and
        signing secrets. Application routes must never fall through to that
        unrestricted behavior.
        """
        raw=unquote(urlparse(request_path or self.path).path)
        if not raw or "\x00" in raw or "\\" in raw:return None
        parts=[part for part in raw.split("/") if part]
        if not parts or any(part in {".",".."} or part.startswith(".") for part in parts):return None
        # Root JSON files are release/build evidence rather than browser assets.
        # Serving arbitrary *.json here disclosed architecture and audit metadata.
        allowed_root_suffixes={".js",".css",".webmanifest",".png",".jpg",".jpeg",".webp",".gif",".svg",".ico",".woff",".woff2",".ttf",".otf",".wasm"}
        allowed_nested_roots={"assets","vendor","licenses"}
        allowed_nested_suffixes=allowed_root_suffixes|{".txt"}
        suffix=Path(parts[-1]).suffix.lower()
        if len(parts)==1:
            if suffix not in allowed_root_suffixes:return None
        elif parts[0] not in allowed_nested_roots or suffix not in allowed_nested_suffixes:return None
        candidate=ROOT.joinpath(*parts).resolve()
        try:candidate.relative_to(ROOT)
        except ValueError:return None
        return candidate if candidate.is_file() else None

    def serve_public_static(self):
        if not self.public_static_path():return self.json(404,{"error":"Not found"})
        return super().do_GET()

    def do_HEAD(self):
        # HEAD must follow the same deny-by-default boundary as GET; otherwise
        # it can still enumerate private files, sizes and modification dates.
        if not self.guard_request_boundary():return
        if self.public_static_path():return super().do_HEAD()
        self.send_response(404);self.send_header("Cache-Control","no-store");self.end_headers()

    def future_v52_error(self, exc):
        if isinstance(exc, FuturePlatformError):
            return self.json(exc.status,{"error":str(exc),"code":exc.code,"requestId":getattr(self,"request_id","")})
        if isinstance(exc, PlatformServiceError):
            return self.json(exc.status,{"error":str(exc),"code":exc.code,"requestId":getattr(self,"request_id","")})
        if JSON_LOGS:
            print(json.dumps({"level":"error","event":"future_v52_request_failed","requestId":getattr(self,"request_id",""),"message":str(exc)},ensure_ascii=False),flush=True)
        return self.json(500,{"error":"Future platform operation failed","code":"future_platform_internal_error","requestId":getattr(self,"request_id","")})
    def future_v52_get(self,path):
        if not path.startswith("/api/platform/v52/"):return False
        try:
            user=self.require_user()
            if not user:return True
            service=get_future_v52_service();query=parse_qs(urlparse(self.path).query)
            result=service.dispatch_get(path,user["id"],query)
            if result is None:return False
            status,payload=result;return self.json(status,payload)
        except Exception as exc:return self.future_v52_error(exc)
    def future_v52_post(self,path):
        if not path.startswith("/api/platform/v52/"):return False
        try:
            user=self.require_user()
            if not user:return True
            service=get_future_v52_service();data=self.body(get_platform_v32_service().config.request_limit_bytes)
            result=service.dispatch_post(path,user["id"],data)
            if result is None:return False
            status,payload=result;return self.json(status,payload)
        except Exception as exc:return self.future_v52_error(exc)

    def platform_v32_error(self, exc):
        if isinstance(exc, PlatformServiceError):
            return self.json(exc.status,{"error":str(exc),"code":exc.code,"requestId":getattr(self,"request_id","")})
        if JSON_LOGS:
            print(json.dumps({"level":"error","event":"platform_v32_request_failed","requestId":getattr(self,"request_id",""),"message":str(exc)},ensure_ascii=False),flush=True)
        return self.json(500,{"error":"Platform operation failed","code":"platform_internal_error","requestId":getattr(self,"request_id","")})
    def platform_v32_user(self):
        user=self.require_user()
        return user
    def platform_v32_get(self,path):
        platform_route=(
            path in {"/api/health/live","/api/health/ready","/api/workspaces"}
            or path.startswith("/api/platform/v32/")
            or bool(re.fullmatch(r"/api/invitations/[^/]+/(?:collaboration/v31/(?:snapshot|updates)|raster/v30/documents)/?",path))
        )
        if not platform_route:return False
        try:
            if path=="/api/health/live":return self.json(200,{"ok":True,"status":"live",**({"version":"0.52"} if DISCLOSE_HEALTH_DETAILS else {})})
            service=get_platform_v32_service()
            if path=="/api/health/ready":
                errors=list(service.config.validate());checks={"configuration":not errors}
                try:
                    with connect() as health_db:health_db.execute("SELECT 1")
                    checks["database"]=True
                except Exception:
                    checks["database"]=False;errors.append("Database readiness probe failed.")
                storage=service.storage.readiness();checks["storage"]=bool(storage.get("ready"))
                if not checks["storage"]:errors.append("Object-storage readiness probe failed.")
                if REDIS_URL:
                    checks["redis"]=bool(redis_client())
                    if not checks["redis"]:errors.append("Redis readiness probe failed.")
                else:checks["redis"]=not PRODUCTION_MODE
                payload={"ok":not errors,"status":"ready" if not errors else "not-ready"}
                if DISCLOSE_HEALTH_DETAILS:payload.update({"errors":errors,"checks":checks,"storage":storage})
                return self.json(200 if not errors else 503,payload)
            object_match=re.fullmatch(r"/api/platform/v32/objects/(.+)",path)
            if object_match:
                key=unquote(object_match.group(1));query=parse_qs(urlparse(self.path).query);expiry=int((query.get("expires") or [0])[0]);disposition=str((query.get("disposition") or ["inline"])[0]);signature=str((query.get("signature") or [""])[0])
                if not service.storage.verify_signature(key,expiry,disposition,signature):return self.json(403,{"error":"Invalid or expired object signature"})
                with connect() as db:stored=db.execute("SELECT mime FROM object_versions WHERE object_key=? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",(key,)).fetchone()
                if not stored:return self.json(404,{"error":"Resource not found"})
                mime=str(stored["mime"] or "application/octet-stream").lower();safe_inline=mime in {"image/jpeg","image/png","image/webp","image/gif","audio/mpeg","audio/mp4","video/mp4","video/webm"}
                if not safe_inline:mime="application/octet-stream";disposition="attachment"
                data=service.storage.read_local(key);self.send_response(200);self.send_header("Content-Type",mime);self.send_header("Content-Length",str(len(data)));self.send_header("Content-Disposition",f'{disposition}; filename="{Path(key).name}"');self.send_header("Cache-Control","private,max-age=60");self.end_headers();return self.safe_write(data)
            user=self.platform_v32_user()
            if not user:return True
            if path=="/api/platform/v32/status":return self.json(200,service.status(user["id"]))
            if path=="/api/workspaces":return self.json(200,service.list_workspaces(user["id"]))
            if path=="/api/platform/v32/jobs":
                query=parse_qs(urlparse(self.path).query);return self.json(200,service.list_jobs(user["id"],int((query.get("limit") or [50])[0])))
            if path=="/api/platform/v32/storage":return self.json(200,service.storage_status(user["id"]))
            if path=="/api/platform/v32/privacy":return self.json(200,service.privacy_status(user["id"]))
            if path=="/api/platform/v32/backups":return self.json(200,service.list_backups(user["id"]))
            backup_preview=re.fullmatch(r"/api/platform/v32/backups/([^/]+)/preview/?",path)
            if backup_preview:return self.json(200,service.backup_preview(user["id"],unquote(backup_preview.group(1))))
            collab_snapshot=re.fullmatch(r"/api/invitations/([^/]+)/collaboration/v31/snapshot/?",path)
            if collab_snapshot:return self.json(200,service.collaboration_snapshot(unquote(collab_snapshot.group(1)),user["id"]))
            collab_updates=re.fullmatch(r"/api/invitations/([^/]+)/collaboration/v31/updates/?",path)
            if collab_updates:
                query=parse_qs(urlparse(self.path).query);since=int((query.get("since") or [0])[0]);return self.json(200,service.collaboration_updates(unquote(collab_updates.group(1)),user["id"],since))
            raster_docs=re.fullmatch(r"/api/invitations/([^/]+)/raster/v30/documents/?",path)
            if raster_docs:return self.json(200,service.list_raster_documents(unquote(raster_docs.group(1)),user["id"]))
        except Exception as exc:return self.platform_v32_error(exc)
        return False
    def platform_v32_post(self,path):
        platform_route=(
            path=="/api/workspaces"
            or path.startswith("/api/platform/v32/")
            or bool(re.fullmatch(r"/api/invitations/[^/]+/(?:collaboration/v31/(?:updates|presence|checkpoints)|raster/v30/documents(?:/[^/]+/render)?)/?",path))
        )
        if not platform_route:return False
        try:
            service=get_platform_v32_service();user=self.platform_v32_user()
            if not user:return True
            if path=="/api/workspaces":
                data=self.body(service.config.request_limit_bytes);return self.json(201,service.create_workspace(user["id"],data.get("name"),data.get("plan","free")))
            if path=="/api/platform/v32/backups":
                data=self.body(service.config.request_limit_bytes);return self.json(202,service.submit_backup(user["id"],data))
            backup_restore=re.fullmatch(r"/api/platform/v32/backups/([^/]+)/restore/?",path)
            if backup_restore:
                data=self.body(service.config.request_limit_bytes);password=str(data.pop("password","") or "")
                with connect() as db:account=db.execute("SELECT password_hash,salt,password_algo FROM users WHERE id=?",(user["id"],)).fetchone()
                valid,_=account_verify_password(password,account["password_hash"],account["salt"],account["password_algo"] if account else "") if account else (False,False)
                if not valid:return self.json(401,{"error":"Password reauthentication failed","code":"reauthentication_failed"})
                return self.json(202,service.submit_restore(user["id"],unquote(backup_restore.group(1)),data,authorized=True))
            if path=="/api/platform/v32/privacy/requests":
                data=self.body(service.config.request_limit_bytes);return self.json(202,service.submit_privacy_request(user["id"],data))
            platform_upload=path=="/api/platform/v32/uploads" or bool(re.fullmatch(r"/api/platform/v32/uploads/[^/]+/(?:parts|complete)/?",path))
            if platform_upload and not self.require_upload_permission(user):return True
            if path=="/api/platform/v32/uploads":
                data=self.body(service.config.request_limit_bytes);return self.json(201,service.create_upload_session(user["id"],data))
            upload_part=re.fullmatch(r"/api/platform/v32/uploads/([^/]+)/parts/?",path)
            if upload_part:
                data=self.body(100000);return self.json(200,service.sign_upload_part(user["id"],unquote(upload_part.group(1)),data))
            upload_complete=re.fullmatch(r"/api/platform/v32/uploads/([^/]+)/complete/?",path)
            if upload_complete:
                data=self.body(service.config.request_limit_bytes);return self.json(200,service.complete_upload_session(user["id"],unquote(upload_complete.group(1)),data))
            job_cancel=re.fullmatch(r"/api/platform/v32/jobs/([^/]+)/cancel/?",path)
            if job_cancel:return self.json(200,{"cancelled":service.jobs.cancel(unquote(job_cancel.group(1)),user["id"])})
            collab_updates=re.fullmatch(r"/api/invitations/([^/]+)/collaboration/v31/updates/?",path)
            if collab_updates:
                data=self.body(service.config.request_limit_bytes);return self.json(200,service.append_collaboration_updates(unquote(collab_updates.group(1)),user["id"],data))
            collab_presence=re.fullmatch(r"/api/invitations/([^/]+)/collaboration/v31/presence/?",path)
            if collab_presence:
                data=self.body(100000);return self.json(200,service.presence_update(unquote(collab_presence.group(1)),user["id"],data))
            collab_checkpoint=re.fullmatch(r"/api/invitations/([^/]+)/collaboration/v31/checkpoints/?",path)
            if collab_checkpoint:
                data=self.body(service.config.request_limit_bytes);return self.json(201,service.create_checkpoint(unquote(collab_checkpoint.group(1)),user["id"],data))
            raster_docs=re.fullmatch(r"/api/invitations/([^/]+)/raster/v30/documents/?",path)
            if raster_docs:
                data=self.body(service.config.request_limit_bytes);return self.json(201,service.save_raster_document(unquote(raster_docs.group(1)),user["id"],data))
            raster_render=re.fullmatch(r"/api/invitations/([^/]+)/raster/v30/documents/([^/]+)/render/?",path)
            if raster_render:
                data=self.body(100000);return self.json(202,service.submit_raster_render(unquote(raster_render.group(1)),user["id"],unquote(raster_render.group(2)),str(data.get("idempotencyKey") or "")))
            object_sign=re.fullmatch(r"/api/platform/v32/objects/sign/?",path)
            if object_sign:
                data=self.body(100000);return self.json(200,service.sign_object_url(user["id"],data,self.origin_base()))
        except Exception as exc:return self.platform_v32_error(exc)
        return False

    def do_GET(self):
        if not self.guard_request_boundary():return
        path = urlparse(self.path).path
        future_result=self.future_v52_get(path)
        if future_result is not False:return future_result
        platform_result=self.platform_v32_get(path)
        if platform_result is not False:return platform_result
        if path == "/favicon.ico":
            self.send_response(204);self.send_header("Cache-Control","public,max-age=86400");self.end_headers();return
        if path=="/":
            host=self.request_host()
            if host:
                with connect() as db:domain_row=db.execute("SELECT slug FROM invitations WHERE custom_domain=? AND is_published=1 AND deleted_at IS NULL AND (expires_at IS NULL OR expires_at>?)",(host,int(time.time()*1000))).fetchone()
                if domain_row:
                    self.send_response(302);self.send_header("Location",f"/i/{quote(domain_row['slug'])}");self.end_headers();return
        management=re.fullmatch(r"/invitations/([^/]+)/(editor|guests|responses|analytics|materials|checkin)/?",path)
        if management:return self.serve_management_page(unquote(management.group(1)),management.group(2))
        if path == "/api/health":
            health={"ok":True}
            if DISCLOSE_HEALTH_DETAILS:
                health.update({"database":DATABASE_KIND,"assetStorage":"object" if object_storage_enabled() else "local","planLimitsEnforced":PLAN_LIMITS_ENFORCED,"redis":bool(redis_client()),"aiConfigured":bool(AI_ENDPOINT),"smtpConfigured":bool(platform_env("EINVITE_SMTP_HOST","").strip() and platform_env("EINVITE_MAIL_FROM","").strip()),"billingWebhookConfigured":bool(BILLING_WEBHOOK_SECRET),"billingCheckoutConfigured":bool(BILLING_CHECKOUT_ENDPOINT),"dependencies":dependency_status(),"uptimeSeconds":int(time.time()-STARTED_AT)})
            return self.json(200,health)
        if path == "/api/ai-agent/status": return self.ai_agent_status()
        if path == "/api/ai-agent/tools": return self.ai_agent_tools()
        if path == "/api/ai-agent/preferences": return self.ai_agent_preferences()
        if path == "/api/ai-agent/memories": return self.ai_agent_memories()
        if path == "/api/ai-agent/knowledge": return self.ai_agent_knowledge()
        ai_blueprints=re.fullmatch(r"/api/invitations/([^/]+)/ai/design-blueprints/?",path)
        if ai_blueprints:return self.ai_agent_list_blueprints(unquote(ai_blueprints.group(1)))
        ai_blueprint=re.fullmatch(r"/api/invitations/([^/]+)/ai/design-blueprints/([^/]+)/?",path)
        if ai_blueprint:return self.ai_agent_get_blueprint(unquote(ai_blueprint.group(1)),unquote(ai_blueprint.group(2)))
        ai_threads=re.fullmatch(r"/api/invitations/([^/]+)/ai/threads/?",path)
        if ai_threads:return self.ai_agent_list_threads(unquote(ai_threads.group(1)))
        ai_thread=re.fullmatch(r"/api/invitations/([^/]+)/ai/threads/([^/]+)/?",path)
        if ai_thread:return self.ai_agent_get_thread(unquote(ai_thread.group(1)),unquote(ai_thread.group(2)))
        if path == "/api/admin/metrics": return self.admin_system_metrics()
        if path == "/api/auth/me":
            user=self.user(); return self.json(200,{"user":dict(user) if user else None})
        if path == "/api/account/export": return self.export_account()
        if path == "/api/account/export/archive": return self.export_account_archive()
        if path == "/api/account/usage": return self.account_usage()
        if path == "/api/billing/status": return self.billing_status()
        if path == "/api/account/security": return self.security_overview()
        if path == "/api/account/studio": return self.get_studio_profile()
        if path == "/api/account/mfa/qr.png": return self.mfa_qr_png()
        if path == "/api/account/sessions": return self.list_sessions()
        if path == "/api/account/passkeys": return self.list_passkeys()
        if path == "/api/account/audit": return self.list_audit_events()
        if path == "/api/admin/overview": return self.admin_overview()
        if path == "/api/admin/ai/providers": return self.admin_ai_providers()
        if path == "/api/admin/users": return self.admin_users()
        if path == "/api/admin/templates": return self.admin_templates()
        if path == "/api/admin/invitations": return self.admin_invitations()
        if path == "/api/invitations": return self.list_invitations()
        if path == "/api/trash": return self.list_trash()
        if path == "/api/template-marketplace": return self.list_marketplace_templates()
        if path.startswith("/api/template-marketplace/") and path.count("/") == 3: return self.get_marketplace_template(path.split("/")[3])
        if path == "/api/templates": return self.list_templates()
        if path == "/api/page-templates": return self.list_page_templates()
        if path == "/api/components": return self.list_components()
        if path == "/api/studio/resources": return self.list_studio_resources()
        if path == "/api/studio/governance": return self.get_studio_governance()
        if path == "/api/studio/releases": return self.list_studio_releases()
        if path == "/api/studio/adoption": return self.studio_release_adoption()
        if path == "/api/studio/audit": return self.studio_operations_audit()
        if path == "/api/studio/backup-policy": return self.get_studio_backup_policy()
        if path == "/api/studio/backups": return self.list_studio_backups()
        if path.startswith("/api/studio/backups/") and path.endswith("/download"): return self.download_studio_backup(path.split("/")[4])
        if path == "/api/studio/bulk-jobs": return self.list_studio_bulk_jobs()
        if path.startswith("/api/invitations/") and path.endswith("/studio-release"): return self.get_invitation_studio_release(path.split("/")[3])
        if path.startswith("/api/templates/") and path.endswith("/versions"): return self.get_template_versions(path.split("/")[3])
        if path.startswith("/api/templates/") and path.count("/") == 3: return self.get_template(path.split("/")[3])
        if path == "/api/assets": return self.get_account_assets()
        if path.startswith("/api/uploads/") and path.count("/")==3: return self.get_upload_session(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/assets"): return self.get_assets(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/materials/folders"): return self.get_material_folders(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/materials/import-jobs"): return self.get_material_import_jobs(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/materials/duplicates"): return self.find_material_duplicates(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.count("/") == 3: return self.get_invitation(path.split("/")[3])
        if path.startswith("/i/"): return self.serve_public(path.split("/", 2)[2])
        if path.startswith("/api/media/"): return self.serve_signed_media(unquote(path[len("/api/media/"):]))
        if path.startswith("/api/image/"): return self.serve_responsive_image(unquote(path[len("/api/image/"):]))
        if path.startswith("/api/public/") and path.endswith("/social-card.svg"): return self.social_card_svg(unquote(path.split("/")[3]))
        if path.startswith("/api/public/") and path.endswith("/social-card.png"): return self.social_card_png(unquote(path.split("/")[3]))
        if path.startswith("/api/public/") and path.endswith("/qr-card.png"): return self.public_qr_card_png(unquote(path.split("/")[3]))
        if path.startswith("/api/public/") and path.endswith("/qr.png"): return self.public_qr_png(unquote(path.split("/")[3]))
        if path.startswith("/api/invitations/") and "/guests/" in path and path.endswith("/qr.png"): return self.guest_qr_png(path.split("/")[3],path.split("/")[5])
        if path.startswith("/api/public/"):
            query=parse_qs(urlparse(self.path).query);guest=self.headers.get("X-Invitation-Guest") or query.get("guest",[None])[0] or query.get("g",[None])[0];access=self.headers.get("X-Invitation-Access") or query.get("access",[None])[0];gallery_access=self.headers.get("X-Gallery-Access")
            return self.get_public(unquote(path.split("/", 3)[3]),guest,access,gallery_access)
        if path.startswith("/api/invitations/") and path.endswith("/guests"): return self.get_guests(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/rsvps"): return self.get_rsvps(path.split("/")[3])
        if path.startswith("/api/invitations/") and re.fullmatch(r"/api/invitations/[^/]+/versions/[^/]+",path): return self.get_version(path.split("/")[3],path.split("/")[5])
        if path.startswith("/api/invitations/") and path.endswith("/versions"): return self.get_versions(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/analytics"): return self.get_analytics(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/wishes"): return self.get_wishes(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/collaborators"): return self.get_collaborators(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/events"): return self.invitation_events(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/presence"): return self.list_presence(path.split("/")[3])
        if path.startswith("/api/invitations/") and re.fullmatch(r"/api/invitations/[^/]+/campaigns/[^/]+/deliveries",path): return self.list_campaign_deliveries(path.split("/")[3],path.split("/")[5])
        if path.startswith("/api/invitations/") and path.endswith("/campaigns"): return self.list_campaigns(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/comments"): return self.get_comments(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/approvals"): return self.list_approvals(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/review-context"): return self.review_context(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/review-tasks"): return self.list_review_tasks(path.split("/")[3])
        if path.startswith("/uploads/"):return self.serve_asset(unquote(path[len("/uploads/"):]))
        if path=="/":return self.serve_html_file("index.html")
        if re.fullmatch(r"/[A-Za-z0-9_.-]+\.html",path):
            return self.serve_html_file(path.lstrip("/"))
        return self.serve_public_static()
    def do_PUT(self):
        if not self.guard_request_boundary():return
        if not self.guard_cookie_origin():return
        path = urlparse(self.path).path
        try:
            if path == "/api/auth/password": return self.change_password()
            if path == "/api/account/studio": return self.update_studio_profile()
            if path == "/api/studio/governance": return self.update_studio_governance()
            if path == "/api/studio/backup-policy": return self.update_studio_backup_policy()
            if path.startswith("/api/invitations/") and path.endswith("/studio-release"): return self.pin_invitation_studio_release(path.split("/")[3])
            if path.startswith("/api/studio/releases/") and path.count("/") == 4: return self.update_studio_release(path.split("/")[4])
            if path.startswith("/api/studio/resources/") and path.count("/") == 4: return self.update_studio_resource(path.split("/")[4])
            if path.startswith("/api/uploads/") and path.count("/")==3: return self.append_upload_chunk(path.split("/")[3])
            if path.startswith("/api/assets/") and path.count("/") == 3: return self.update_asset(path.split("/")[3])
            if path.startswith("/api/admin/users/") and path.endswith("/role"): return self.admin_update_user_role(path.split("/")[4])
            if path.startswith("/api/admin/users/") and path.endswith("/plan"): return self.admin_update_user_plan(path.split("/")[4])
            if path.startswith("/api/admin/users/") and path.endswith("/uploads"): return self.admin_update_user_upload_permission(path.split("/")[4])
            if path.startswith("/api/admin/templates/") and path.endswith("/visibility"): return self.admin_update_template_visibility(path.split("/")[4])
            if path.startswith("/api/admin/invitations/") and path.endswith("/published"): return self.admin_update_invitation_published(path.split("/")[4])
            if "/guests/" in path and path.endswith("/check-in"): return self.check_in_guest(path.split("/")[3],path.split("/")[5])
            if "/rsvps/" in path: return self.update_rsvp(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/templates/") and path.count("/") == 3: return self.update_template(path.split("/")[3])
            if path.startswith("/api/page-templates/") and path.count("/") == 3: return self.update_page_template(path.split("/")[3])
            if path.startswith("/api/components/") and path.count("/") == 3: return self.update_component(path.split("/")[3])
            if path.startswith("/api/invitations/") and "/guests/" in path and path.count("/")==5: return self.update_guest_details(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/invitations/") and "/comments/" in path and path.count("/")==5: return self.resolve_comment(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/invitations/") and "/approvals/" in path and path.count("/")==5: return self.decide_approval(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/invitations/") and path.endswith("/review-policy"): return self.update_review_policy(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/review-notifications"): return self.mark_review_notifications(path.split("/")[3])
            if path.startswith("/api/invitations/") and "/review-tasks/" in path and path.count("/")==5: return self.update_review_task(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/invitations/") and path.endswith("/operations"): return self.update_invitation_operations(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/archive"): return self.archive_invitation(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/slug"): return self.update_slug(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/access"): return self.update_access(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/gallery-access"): return self.update_gallery_access(path.split("/")[3])
            if path.startswith("/api/invitations/"): return self.save_draft(path.split("/")[3])
            self.json(404, {"error": "Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.json(400, {"error": str(exc)})
    def do_DELETE(self):
        if not self.guard_request_boundary():return
        if not self.guard_cookie_origin():return
        path=urlparse(self.path).path
        try:
            if path.startswith("/api/account/sessions/") and path.count("/")==4:return self.revoke_session(path.split("/")[4] if len(path.split("/"))>4 else path.rsplit("/",1)[-1])
            if path.startswith("/api/account/passkeys/") and path.count("/")==4:return self.delete_passkey(path.rsplit("/",1)[-1])
            if path.startswith("/api/uploads/") and path.count("/")==3:return self.cancel_resumable_upload(path.split("/")[3])
            material_cancel=re.fullmatch(r"/api/invitations/([^/]+)/materials/import-jobs/([^/]+)",path)
            if material_cancel:return self.cancel_material_import_job(unquote(material_cancel.group(1)),unquote(material_cancel.group(2)))
            if path.startswith("/api/invitations/") and "/comments/" in path and path.count("/")==5:return self.delete_comment(path.split("/")[3],path.split("/")[5])
            if "/assets/" in path:return self.delete_asset(path.split("/")[3],path.split("/")[5])
            if "/guests/" in path:return self.delete_guest(path.split("/")[3],path.split("/")[5])
            if "/rsvps/" in path:return self.delete_rsvp(path.split("/")[3],path.split("/")[5])
            if "/wishes/" in path:return self.delete_wish(path.split("/")[3],path.split("/")[5])
            if "/collaborators/" in path:return self.delete_collaborator(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/page-templates/"): return self.delete_page_template(path.split("/")[3])
            if path.startswith("/api/components/"): return self.delete_component(path.split("/")[3])
            if path.startswith("/api/studio/resources/") and path.count("/") == 4: return self.delete_studio_resource(path.split("/")[4])
            if path.startswith("/api/studio/releases/") and path.count("/") == 4: return self.delete_studio_release(path.split("/")[4])
            if path.startswith("/api/templates/"): return self.delete_template(path.split("/")[3])
            if path.startswith("/api/invitations/"): return self.delete_invitation(path.split("/")[3])
            self.json(404,{"error":"Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.json(400, {"error": str(exc)})
    def do_POST(self):
        if not self.guard_request_boundary():return
        path = urlparse(self.path).path
        if path.startswith("/api/platform/v52/"):
            if not self.guard_cookie_origin():return
            future_result=self.future_v52_post(path)
            if future_result is not False:return future_result
        if path.startswith("/api/platform/v32/") or path=="/api/workspaces" or "/collaboration/v31/" in path or "/raster/v30/" in path:
            if not self.guard_cookie_origin():return
            platform_result=self.platform_v32_post(path)
            if platform_result is not False:return platform_result
        csrf_exempt={
            "/api/auth/register","/api/auth/login","/api/auth/mfa/complete",
            "/api/auth/passkeys/login/options","/api/auth/passkeys/login/complete",
            "/api/auth/password-reset/request","/api/auth/password-reset/confirm",
            "/api/auth/verification/confirm","/api/billing/webhook",
        }
        # Public guest actions are deliberately unauthenticated.  A host may
        # preview their own invitation while still carrying an account cookie;
        # that incidental cookie must not turn an RSVP, wish, view, or unlock
        # request into an authenticated CSRF-protected account mutation.
        # Origin/Sec-Fetch-Site validation still applies to every browser POST.
        public_guest_action=path.startswith("/api/public/") and any(path.endswith(suffix) for suffix in (
            "/rsvps","/wishes","/view","/unlock","/gallery/unlock"
        ))
        if not self.guard_cookie_origin(require_session_csrf=path not in csrf_exempt and not public_guest_action):return
        try:
            if path == "/api/auth/register": return self.register()
            if path == "/api/auth/login": return self.login()
            if path == "/api/auth/logout": return self.logout()
            if path == "/api/auth/mfa/complete": return self.complete_mfa_login()
            if path == "/api/auth/passkeys/login/options": return self.passkey_login_options()
            if path == "/api/auth/passkeys/login/complete": return self.passkey_login_complete()
            if path == "/api/auth/password-reset/request": return self.request_password_reset()
            if path == "/api/auth/password-reset/confirm": return self.confirm_password_reset()
            if path == "/api/auth/verification/request": return self.request_email_verification()
            if path == "/api/auth/verification/confirm": return self.confirm_email_verification()
            if path == "/api/account/mfa/setup": return self.mfa_setup()
            if path == "/api/account/mfa/enable": return self.mfa_enable()
            if path == "/api/account/mfa/disable": return self.mfa_disable()
            if path == "/api/account/passkeys/register/options": return self.passkey_register_options()
            if path == "/api/account/passkeys/register/complete": return self.passkey_register_complete()
            if path == "/api/account/sessions/revoke-all": return self.revoke_all_sessions()
            if path == "/api/account/privacy": return self.update_privacy_preferences()
            if path == "/api/ai-agent/preferences": return self.ai_agent_update_preferences()
            if path == "/api/ai-agent/memories": return self.ai_agent_add_memory()
            if path == "/api/ai-agent/knowledge": return self.ai_agent_add_knowledge()
            ai_delete_memory=re.fullmatch(r"/api/ai-agent/memories/([^/]+)/delete/?",path)
            if ai_delete_memory:return self.ai_agent_delete_memory(unquote(ai_delete_memory.group(1)))
            ai_delete_knowledge=re.fullmatch(r"/api/ai-agent/knowledge/([^/]+)/delete/?",path)
            if ai_delete_knowledge:return self.ai_agent_delete_knowledge(unquote(ai_delete_knowledge.group(1)))
            ai_design_blueprint_create=re.fullmatch(r"/api/invitations/([^/]+)/ai/design-blueprints/([^/]+)/create-invitation/?",path)
            if ai_design_blueprint_create:return self.ai_agent_create_invitation_from_blueprint(unquote(ai_design_blueprint_create.group(1)),unquote(ai_design_blueprint_create.group(2)))
            ai_design_blueprint=re.fullmatch(r"/api/invitations/([^/]+)/ai/design-blueprints/?",path)
            if ai_design_blueprint:return self.ai_agent_analyze_reference(unquote(ai_design_blueprint.group(1)))
            ai_create_thread=re.fullmatch(r"/api/invitations/([^/]+)/ai/threads/?",path)
            if ai_create_thread:return self.ai_agent_create_thread(unquote(ai_create_thread.group(1)))
            ai_message=re.fullmatch(r"/api/invitations/([^/]+)/ai/threads/([^/]+)/messages/?",path)
            if ai_message:return self.ai_agent_stream_message(unquote(ai_message.group(1)),unquote(ai_message.group(2)))
            ai_feedback=re.fullmatch(r"/api/invitations/([^/]+)/ai/messages/([^/]+)/feedback/?",path)
            if ai_feedback:return self.ai_agent_feedback(unquote(ai_feedback.group(1)),unquote(ai_feedback.group(2)))
            ai_archive=re.fullmatch(r"/api/invitations/([^/]+)/ai/threads/([^/]+)/archive/?",path)
            if ai_archive:return self.ai_agent_archive_thread(unquote(ai_archive.group(1)),unquote(ai_archive.group(2)))
            ai_confirm=re.fullmatch(r"/api/invitations/([^/]+)/ai/plans/([^/]+)/confirm/?",path)
            if ai_confirm:return self.ai_agent_confirm_plan(unquote(ai_confirm.group(1)),unquote(ai_confirm.group(2)))
            ai_authorize=re.fullmatch(r"/api/invitations/([^/]+)/ai/plans/([^/]+)/authorize/?",path)
            if ai_authorize:return self.ai_agent_authorize_tool(unquote(ai_authorize.group(1)),unquote(ai_authorize.group(2)))
            ai_cancel_plan=re.fullmatch(r"/api/invitations/([^/]+)/ai/plans/([^/]+)/cancel/?",path)
            if ai_cancel_plan:return self.ai_agent_cancel_plan(unquote(ai_cancel_plan.group(1)),unquote(ai_cancel_plan.group(2)))
            ai_complete=re.fullmatch(r"/api/invitations/([^/]+)/ai/plans/([^/]+)/complete/?",path)
            if ai_complete:return self.ai_agent_complete_plan(unquote(ai_complete.group(1)),unquote(ai_complete.group(2)))
            ai_cancel_job=re.fullmatch(r"/api/invitations/([^/]+)/ai/jobs/([^/]+)/cancel/?",path)
            if ai_cancel_job:return self.ai_agent_cancel_job(unquote(ai_cancel_job.group(1)),unquote(ai_cancel_job.group(2)))
            if path == "/api/account/delete/schedule": return self.schedule_account_deletion()
            if path == "/api/account/delete/cancel": return self.cancel_account_deletion()
            if path == "/api/ai/assist": return self.ai_assist()
            if path == "/api/billing/webhook": return self.billing_webhook()
            if path == "/api/billing/checkout": return self.billing_checkout()
            if path == "/api/invitations": return self.create_invitation()
            if path == "/api/templates": return self.create_template()
            if path == "/api/page-templates": return self.create_page_template()
            if path == "/api/components": return self.create_component()
            if path == "/api/studio/resources": return self.create_studio_resource()
            if path == "/api/studio/releases": return self.create_studio_release()
            if path.startswith("/api/studio/releases/") and path.endswith("/activate"): return self.activate_studio_release(path.split("/")[4])
            if path.startswith("/api/studio/releases/") and path.endswith("/clone"): return self.clone_studio_release(path.split("/")[4])
            if path.startswith("/api/studio/releases/") and path.endswith("/bulk-pin"): return self.bulk_pin_studio_release(path.split("/")[4])
            if path == "/api/studio/backups/run": return self.run_studio_backup_now()
            if path.startswith("/api/templates/") and path.endswith("/duplicate"): return self.duplicate_template(path.split("/")[3])
            if path.startswith("/api/templates/") and path.endswith("/restore"): return self.restore_template_version(path.split("/")[3])
            if path.startswith("/api/public/") and path.endswith("/gallery/unlock"): return self.unlock_public_gallery(unquote(path.split("/")[3]))
            if path.startswith("/api/public/") and path.endswith("/view"): return self.record_public_view(unquote(path.split("/")[3]))
            if path.startswith("/api/public/") and path.endswith("/unlock"): return self.unlock_public(unquote(path.split("/")[3]))
            if path.startswith("/api/invitations/") and path.endswith("/publish"): return self.publish(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/trash"): return self.trash_invitation(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/restore"): return self.restore_trashed_invitation(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/unpublish"): return self.unpublish(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/materials/folders"): return self.create_material_folder(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/materials/import-jobs"): return self.start_material_import_job(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/materials/import-zip"): return self.import_material_zip(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/materials/move"): return self.move_material(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/materials/rename"): return self.rename_material(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/materials/classify"): return self.classify_materials(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/rsvp-config"): return self.configure_rsvp(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/ai/guest-delivery-status"): return self.ai_guest_delivery_status(path.split("/")[3])
            material_failure=re.fullmatch(r"/api/invitations/([^/]+)/materials/import-jobs/([^/]+)/failure/?",path)
            if material_failure:return self.report_material_import_failure(unquote(material_failure.group(1)),unquote(material_failure.group(2)))
            if path.startswith("/api/invitations/") and path.endswith("/uploads/start"): return self.start_resumable_upload(path.split("/")[3])
            if path.startswith("/api/uploads/") and path.endswith("/complete"): return self.complete_resumable_upload(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/guests") and path.count("/")==4: return self.add_guest(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/token/rotate") and "/guests/" in path: return self.rotate_guest_token(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/invitations/") and path.endswith("/token/revoke") and "/guests/" in path: return self.revoke_guest_token(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/invitations/") and path.endswith("/assets/presign"): return self.presign_asset_upload(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets/complete"): return self.complete_presigned_asset(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/fonts"): return self.upload_font(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets/raw"): return self.upload_raw(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets"): return self.upload(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/collaborators"): return self.add_collaborator(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/presence"): return self.update_presence(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/campaigns"): return self.create_campaign(path.split("/")[3])
            if path.startswith("/api/invitations/") and "/campaigns/" in path and path.endswith("/dispatch"): return self.dispatch_campaign(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/invitations/") and path.endswith("/comments"): return self.add_comment(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/approvals"): return self.request_approval(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/restore-version"): return self.restore_published_version(path.split("/")[3])
            if path.startswith("/api/public/") and path.endswith("/wishes"): return self.submit_wish(unquote(path.split("/")[3]))
            if path.startswith("/api/public/") and path.endswith("/rsvps"): return self.rsvp(unquote(path.split("/")[3]))
            self.json(404, {"error": "Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc: self.json(400, {"error": str(exc)})
    def _ai_agent_access(self, invite_id=None, edit=False):
        user=self.require_user()
        if not user:return None,None
        if invite_id:
            with connect() as db:
                allowed=self.can_edit_invitation(db,invite_id,user["id"]) if edit else self.can_read_invitation(db,invite_id,user["id"])
                role=self.invitation_role(db,invite_id,user["id"]) if allowed else ""
            if not allowed:
                self.json(403,{"error":"Invitation access is required","code":"ai_invitation_access_required"});return None,None
        else:role=str(user["role"] if "role" in user.keys() else "customer")
        return user,role

    def _ai_agent_json_call(self, callback):
        try:return callback()
        except AgentServiceError as exc:return self.json(exc.status,exc.payload())

    def ai_agent_status(self):
        user,role=self._ai_agent_access()
        if not user:return
        query=parse_qs(urlparse(self.path).query);invite_id=str(query.get("invitationId",[""])[0])[:120]
        if invite_id:
            with connect() as db:
                if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation access is required"})
        return self.json(200,get_ai_agent_service().status(user["id"],invite_id or None))

    def ai_agent_tools(self):
        query=parse_qs(urlparse(self.path).query);invite_id=str(query.get("invitationId",[""])[0])[:120]
        user,role=self._ai_agent_access(invite_id) if invite_id else self._ai_agent_access()
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().capability_catalog(user["id"],invite_id,role if invite_id else "")))

    def ai_agent_preferences(self):
        user,role=self._ai_agent_access()
        if not user:return
        return self.json(200,get_ai_agent_service().status(user["id"])["preferences"])

    def ai_agent_update_preferences(self):
        user,role=self._ai_agent_access()
        if not user:return
        data=self.body(20_000)
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().update_preferences(user["id"],data)))

    def ai_agent_memories(self):
        user,role=self._ai_agent_access()
        if not user:return
        query=parse_qs(urlparse(self.path).query);invite_id=str(query.get("invitationId",[""])[0])[:120]
        if invite_id:
            with connect() as db:
                if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation access is required"})
        return self._ai_agent_json_call(lambda:self.json(200,{"memories":get_ai_agent_service().list_memories(user["id"],invite_id)}))

    def ai_agent_add_memory(self):
        user,role=self._ai_agent_access()
        if not user:return
        data=self.body(20_000);invite_id=str(data.get("invitationId") or "")[:120]
        if str(data.get("scope") or "account")=="invitation":
            if not invite_id:return self.json(400,{"error":"Invitation-scoped memory requires an invitation"})
            with connect() as db:
                if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation access is required"})
        return self._ai_agent_json_call(lambda:self.json(201,get_ai_agent_service().add_memory(user["id"],data)))

    def ai_agent_delete_memory(self,memory_id):
        user,role=self._ai_agent_access()
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,{"deleted":get_ai_agent_service().delete_memory(user["id"],memory_id)}))

    def ai_agent_knowledge(self):
        user,role=self._ai_agent_access()
        if not user:return
        query=parse_qs(urlparse(self.path).query);invite_id=str(query.get("invitationId",[""])[0])[:120]
        if invite_id:
            with connect() as db:
                if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation access is required"})
        return self._ai_agent_json_call(lambda:self.json(200,{"sources":get_ai_agent_service().list_knowledge_sources(user["id"],invite_id)}))

    def ai_agent_add_knowledge(self):
        user,role=self._ai_agent_access()
        if not user:return
        data=self.body(120_000);invite_id=str(data.get("invitationId") or "")[:120]
        if str(data.get("scope") or "invitation")=="invitation":
            if not invite_id:return self.json(400,{"error":"Invitation-scoped knowledge requires an invitation"})
            with connect() as db:
                if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation access is required"})
        return self._ai_agent_json_call(lambda:self.json(201,get_ai_agent_service().add_knowledge_source(user["id"],data)))

    def ai_agent_delete_knowledge(self,source_id):
        user,role=self._ai_agent_access()
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,{"deleted":get_ai_agent_service().delete_knowledge_source(user["id"],source_id)}))

    def ai_agent_feedback(self,invite_id,message_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        data=self.body(20_000)
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().record_feedback(invite_id,user["id"],message_id,data)))

    def ai_agent_list_blueprints(self,invite_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,{"blueprints":get_ai_agent_service().list_blueprints(invite_id,user["id"])}))

    def ai_agent_get_blueprint(self,invite_id,blueprint_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().get_blueprint(invite_id,user["id"],blueprint_id)))

    def ai_agent_analyze_reference(self,invite_id):
        user,role=self._ai_agent_access(invite_id,edit=True)
        if not user:return
        data=self.body(50_000)
        return self._ai_agent_json_call(lambda:self.json(201,get_ai_agent_service().analyze_reference(invite_id,user["id"],role,data)))

    def ai_agent_create_invitation_from_blueprint(self,invite_id,blueprint_id):
        user,role=self._ai_agent_access(invite_id,edit=True)
        if not user:return
        data=self.body(20_000)
        try:record=get_ai_agent_service().get_blueprint(invite_id,user["id"],blueprint_id)
        except AgentServiceError as exc:return self.json(exc.status,exc.payload())
        blueprint=record.get("blueprint") if isinstance(record,dict) else {}
        blueprint=blueprint if isinstance(blueprint,dict) else {}
        colors=[]
        for value in blueprint.get("colorPalette") or []:
            value=str(value or "").upper()
            if re.fullmatch(r"#[0-9A-F]{6}",value) and value not in colors:colors.append(value)
            if len(colors)>=4:break
        background=colors[0] if colors else "#FFF8F2";heading=colors[1] if len(colors)>1 else "#5A3214";accent=colors[2] if len(colors)>2 else heading;text=colors[3] if len(colors)>3 else "#302B27"
        category=re.sub(r"[^A-Za-z0-9 _-]+","",str(blueprint.get("detectedInvitationCategory") or "Invitation")).strip()[:80] or "Invitation"
        title=str(data.get("newInvitationTitle") or f"{category} Invitation").strip()[:180] or f"{category} Invitation"
        page_id=f"ai-page-{uuid.uuid4().hex[:12]}";title_id=f"ai-title-{uuid.uuid4().hex[:12]}";accent_id=f"ai-accent-{uuid.uuid4().hex[:12]}"
        document={
            "schemaVersion":27,"eventType":category,"fields":{"names":title,"namesKm":"","date":"","time":"","venue":"","venueKm":"","message":"","messageKm":""},
            "settings":{"rsvpEnabled":False,"wishesEnabled":True,"scheduleEnabled":True,"venueEnabled":True,"galleryEnabled":True,"countdownEnabled":True,"musicEnabled":False,"openingEnabled":True,"contactEnabled":True},
            "languageMode":"both","dateFormat":"both","khmerDate":"","mapUrl":"","schedule":[],"venues":[],"customBlocks":[],"objects":{},
            "palette":{"background":background,"surface":"#FFFFFF","text":text,"heading":heading},"accent":accent,
            "masterPageStyle":{"enabled":False,"background":background,"backgroundImage":"","backgroundSize":"cover","backgroundOverlay":0},
            "designPages":[{"id":page_id,"name":f"AI {category}"[:120],"preset":"ai-blueprint","enabled":True,"background":background,"backgroundImage":"","backgroundSize":"cover","backgroundOverlay":0,"useMasterBackground":False,"animation":{"preset":"fade-up","duration":900},"transition":{"preset":"soft","duration":600},"objects":{
                title_id:{"type":"text","semanticRole":"display","html":title,"left":"10%","top":"15%","width":"80%","height":"180px","fontSize":42,"textStyleId":"display","textAlign":"center","textVerticalAlign":"middle","textAutoFit":"fit","textAutoFitMax":42,"textMinFontSize":20,"color":heading,"visible":True,"locked":False,"zIndex":2},
                accent_id:{"type":"shape","semanticRole":"decoration","html":"","left":"25%","top":"42%","width":"50%","height":"12px","fillColor":accent,"visible":True,"locked":False,"zIndex":1}
            }}],
            "sectionOrder":[f"page:{page_id}","schedule","venue","rsvp"],"rsvpFields":[]
        }
        document=validate_document(document)
        if bool(data.get("previewOnly")):
            return self.json(200,{"previewOnly":True,"blueprintId":blueprint_id,"document":document,"createdInvitationId":"","slug":""})
        if not self.require_plan_capacity(user,"invitations"):return
        invite_id_new=str(uuid.uuid4());slug=clean_slug(data.get("slug") or f"ai-{category.lower().replace(' ','-')}");now=int(time.time()*1000);workspace=get_platform_v32_service().workspace_for_user(user["id"])
        with connect() as db:
            base=slug;n=2
            while db.execute("SELECT 1 FROM invitations WHERE slug=?",(slug,)).fetchone():slug=f"{base}-{n}";n+=1
            db.execute("INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,workspace_id,document_epoch,document_version) VALUES(?,?,?,?,?,?,1,0)",(invite_id_new,slug,json.dumps(document),now,user["id"],workspace["id"]))
        self.audit("ai.blueprint_invitation_created","invitation",invite_id_new,{"sourceInvitationId":invite_id,"blueprintId":blueprint_id})
        self.json(201,{"previewOnly":False,"blueprintId":blueprint_id,"createdInvitationId":invite_id_new,"slug":slug,"updatedAt":now,"url":f"/invitations/{invite_id_new}/editor"})

    def ai_agent_list_threads(self,invite_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,{"threads":get_ai_agent_service().list_threads(invite_id,user["id"])}))

    def ai_agent_get_thread(self,invite_id,conversation_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().get_thread(invite_id,user["id"],conversation_id)))

    def ai_agent_create_thread(self,invite_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        data=self.body(20_000);title=str(data.get("title") or "New agent chat")[:160]
        return self._ai_agent_json_call(lambda:self.json(201,get_ai_agent_service().create_thread(invite_id,user["id"],title)))

    def ai_agent_archive_thread(self,invite_id,conversation_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,{"archived":get_ai_agent_service().archive_thread(invite_id,user["id"],conversation_id)}))

    def ai_agent_stream_message(self,invite_id,conversation_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        data=self.body(300_000)
        if not self.rate_limit(f"ai-agent:{user['id']}",120,3600):return
        # Context/storage/provider setup is lazy because stream_message is a generator.
        # Advance it before NDJSON headers so unexpected pre-stream failures can still
        # return a normal, sanitized JSON response rather than aborting the socket.
        try:
            events=get_ai_agent_service().stream_message(invite_id,user["id"],role,conversation_id,data)
            iterator=iter(events)
            first=next(iterator)
        except StopIteration:
            return self.json(500,{"error":"The AI agent could not start safely.","code":"agent_internal_error"})
        except AgentServiceError as exc:
            return self.json(exc.status,exc.payload())
        except Exception:
            return self.json(500,{"error":"The AI agent could not start safely.","code":"agent_internal_error"})
        self.send_response(200);self.send_header("Content-Type","application/x-ndjson; charset=utf-8");self.send_header("Cache-Control","no-store, no-transform");self.send_header("X-Accel-Buffering","no");self.end_headers()
        if not self.safe_write(first):
            try:iterator.close()
            except Exception:pass
            return
        try:
            self.wfile.flush()
            for chunk in iterator:
                if not self.safe_write(chunk):break
                self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            pass
        except Exception:
            # Headers are already committed: terminate with one valid sanitized NDJSON
            # error event. The agent service owns job finalization/release semantics.
            terminal=(json.dumps({"type":"error","timestamp":int(time.time()*1000),"code":"agent_internal_error","message":"The AI agent stream ended safely after an internal error."},ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
            self.safe_write(terminal)
            try:self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
        finally:
            try:iterator.close()
            except Exception:pass

    def ai_agent_confirm_plan(self,invite_id,plan_id):
        user,role=self._ai_agent_access(invite_id,edit=True)
        if not user:return
        data=self.body(100_000)
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().confirm_plan(invite_id,user["id"],role,plan_id,data)))

    def ai_agent_authorize_tool(self,invite_id,plan_id):
        user,role=self._ai_agent_access(invite_id,edit=True)
        if not user:return
        data=self.body(100_000)
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().authorize_tool_call(invite_id,user["id"],role,plan_id,data)))

    def ai_agent_cancel_plan(self,invite_id,plan_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().cancel_plan(invite_id,user["id"],plan_id)))

    def ai_agent_complete_plan(self,invite_id,plan_id):
        user,role=self._ai_agent_access(invite_id,edit=True)
        if not user:return
        data=self.body(50_000)
        return self._ai_agent_json_call(lambda:self.json(200,get_ai_agent_service().complete_plan(invite_id,user["id"],plan_id,data)))

    def ai_agent_cancel_job(self,invite_id,job_id):
        user,role=self._ai_agent_access(invite_id)
        if not user:return
        return self._ai_agent_json_call(lambda:self.json(200,{"cancelled":get_ai_agent_service().cancel_job(invite_id,user["id"],job_id)}))

    def local_ai_response(self, task, prompt, context):
        """Return bounded deterministic templates; never masquerade prompt echo as generative AI."""
        prompt=str(prompt or "").strip();context=context if isinstance(context,dict) else {}
        aliases={"translate-km":"translate-khmer","translate-en":"translate-english","formal":"rewrite-formal","romantic":"rewrite-romantic"}
        task=aliases.get(str(task or "").strip(),str(task or "").strip())
        names=str(context.get("names") or "the hosts").strip();names_km=str(context.get("namesKm") or names).strip();event_type=str(context.get("eventType") or "event").strip().lower();venue=str(context.get("venue") or "").strip();venue_km=str(context.get("venueKm") or venue).strip();date=str(context.get("date") or "").strip();selected=str(context.get("selectedText") or "").strip()
        date_text=(' on '+date) if date else '';venue_text=(' at '+venue) if venue else ''
        if task=="translate-khmer":return f"យើងខ្ញុំ {names_km} និងក្រុមគ្រួសារ សូមគោរពអញ្ជើញលោកអ្នក និងក្រុមគ្រួសារ ចូលរួមជាភ្ញៀវកិត្តិយសក្នុង{('ពិធីមង្គលការ' if event_type=='wedding' else 'កម្មវិធីដ៏មានអត្ថន័យ')}របស់យើង{(' ដែលប្រារព្ធនៅ '+venue_km) if venue_km else ''}។ វត្តមានដ៏ថ្លៃថ្លារបស់លោកអ្នក គឺជាកិត្តិយស និងសេចក្តីរីករាយដ៏ធំធេងសម្រាប់យើងខ្ញុំ។"
        if task=="translate-english":return str(context.get("message") or "").strip() or f"You are warmly invited to celebrate this special {event_type} with {names}. Your presence would make the occasion even more meaningful."
        if task=="rewrite-formal":return f"Together with our families, {names} respectfully request the honour of your presence at our special {event_type}{date_text}{venue_text}. Your presence would be deeply appreciated."
        if task=="rewrite-romantic":return f"With joyful hearts and the love of our families, {names} invite you to share in a beautiful celebration filled with love, laughter, and memories we will cherish forever{date_text}{venue_text}."
        if task=="tone-friendly":return f"{names} would love for you to join us for a very special celebration{date_text}{venue_text}. Come share the joy, make beautiful memories, and celebrate together with us."
        if task=="shorten":return (selected[:180].rsplit(' ',1)[0]+'…') if len(selected)>190 else (selected or f"Join {names} for a beautiful celebration{date_text}{venue_text}.")
        if task=="schedule":return "4:00 PM | Guest arrival\n5:00 PM | Main ceremony\n6:30 PM | Dinner reception\n8:00 PM | Celebration and photos"
        if task=="page-outline":return "1. Opening — names, event type and one strong visual\n2. Invitation message — short welcoming wording\n3. Story or photo feature — optional personal moment\n4. Event details — date, time and ceremony information\n5. Schedule — guest-friendly timeline\n6. Venue — address and map link\n7. RSVP — only when attendance confirmation is needed\n8. Thank you — closing message and contact details"
        if task=="design":return "Design direction: elegant contemporary celebration.\nPalette: #F6EFE7 warm ivory, #B99252 muted gold, #6F3144 deep burgundy.\nTypography: one ceremonial Khmer display face for major headings, a refined serif for English names, and a clean sans-serif for details.\nLayout: one focal point per page with generous spacing and short text blocks.\nMotion: subtle fade-up and soft zoom; avoid animating every object differently."
        if task=="design-review":return "Review the current canvas for one clear focal point, readable text sizes, controlled font and color usage, comfortable spacing, and consistent alignment. Keep detailed guest information in dedicated sections instead of crowding the hero page."
        if task=="accessibility":return "Keep date, venue, schedule and RSVP instructions as real text; add meaningful image descriptions; avoid very small text; maintain strong text/background contrast; and preview the invitation on mobile before publishing."
        if task=="write":return f"Together with our families, {names} warmly invite you to celebrate our special {event_type}{date_text}{venue_text}. We would be honoured to share this meaningful occasion with you."
        raise ValueError("Unsupported assistant task")

    def ai_assist(self):
        user=self.require_user()
        if not user:return
        if not self.rate_limit(f"ai:{user['id']}",60,3600):return
        data=self.body(300_000);task=str(data.get("task","") or "write")[:80];prompt=str(data.get("prompt","") or "")[:20_000];context=data.get("context",{})
        if not isinstance(context,dict):context={}
        invite_id=str(context.get("invitationId") or "")[:120]
        if invite_id:
            with connect() as db:
                if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation access is required"})
        context={**context,"learning":get_ai_agent_service().store.learning_context(user["id"],invite_id,prompt)}
        aliases={"translate-km":"translate-khmer","translate-en":"translate-english","formal":"rewrite-formal","romantic":"rewrite-romantic"};task=aliases.get(task,task)
        allowed={"write","rewrite-formal","rewrite-romantic","shorten","tone-friendly","translate-khmer","translate-english","schedule","page-outline","design","design-review","accessibility"}
        if task not in allowed:return self.json(400,{"error":"Unsupported assistant task"})
        fallback_message=""
        if AI_ENDPOINT:
            payload=json.dumps({"task":task,"prompt":prompt,"context":context,"model":AI_MODEL or None},ensure_ascii=False).encode()
            headers={"Content-Type":"application/json","User-Agent":"E-invitation-website/1.0"}
            if AI_API_KEY:headers["Authorization"]=f"Bearer {AI_API_KEY}"
            try:
                request=urllib.request.Request(AI_ENDPOINT,data=payload,headers=headers,method="POST")
                with urllib.request.urlopen(request,timeout=AI_TIMEOUT) as response:result=json.loads(response.read(2_000_000) or b"{}")
                if not isinstance(result,dict):raise ValueError("Provider returned an invalid response shape")
                output=result.get("text") or result.get("output") or result.get("output_text")
                if not output and isinstance(result.get("choices"),list) and result["choices"]:
                    first=result["choices"][0];output=((first.get("message") or {}).get("content") if isinstance(first,dict) else None) or (first.get("text") if isinstance(first,dict) else None)
                if isinstance(output,list):output="\n".join(str(x.get("text",x) if isinstance(x,dict) else x) for x in output[:200])
                if not isinstance(output,str) or not output.strip():raise ValueError("Provider returned no usable text")
                return self.json(200,{"text":output.strip()[:50_000],"provider":"external","providerMode":"connected"})
            except Exception as exc:
                fallback_message="Connected provider was unavailable; a deterministic offline template was used."
                if JSON_LOGS:print(json.dumps({"level":"warning","event":"ai_provider_failed","errorType":type(exc).__name__},ensure_ascii=False),flush=True)
        return self.json(200,{"text":self.local_ai_response(task,prompt,context),"provider":"template","providerMode":"fallback" if fallback_message else "offline",**({"providerMessage":fallback_message} if fallback_message else {})})

    def billing_status(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            orders=[dict(row) for row in db.execute("SELECT id,plan,status,provider,amount_minor,currency,created_at,updated_at,paid_at FROM billing_orders WHERE user_id=? ORDER BY created_at DESC LIMIT 10",(user["id"],)).fetchall()]
        self.json(200,{
            "configured":bool(BILLING_CHECKOUT_ENDPOINT and BILLING_WEBHOOK_SECRET),
            "provider":BILLING_PROVIDER_NAME,
            "currency":BILLING_CURRENCY,
            "prices":BILLING_PLAN_PRICES,
            "paymentMethods":["visa","mastercard"],
            "hostedCheckout":True,
            "orders":orders,
        })

    def billing_checkout(self):
        user=self.require_user()
        if not user:return
        if REQUIRE_VERIFIED_EMAIL and not self.require_verified_for_sensitive_action(user,"starting checkout"):return
        data=self.body(50_000);plan=str(data.get("plan","")).lower()
        if plan not in {"creator","studio"}:raise ValueError("Unsupported checkout plan")
        if not BILLING_CHECKOUT_ENDPOINT or not BILLING_WEBHOOK_SECRET:return self.json(503,{"error":"Secure card checkout is not configured yet"})
        now=int(time.time()*1000);order_id="ord_"+uuid.uuid4().hex
        amount_minor=BILLING_PLAN_PRICES[plan]
        if amount_minor<=0:return self.json(503,{"error":"The selected plan does not have a configured price"})
        base=self.origin_base().rstrip("/")
        payload=json.dumps({
            "orderId":order_id,"userId":user["id"],"email":user["email"],"plan":plan,
            "amountMinor":amount_minor,"currency":BILLING_CURRENCY,"paymentMethods":["card"],
            "returnUrl":base+"/billing.html?checkout=success&order="+quote(order_id),
            "cancelUrl":base+"/billing.html?checkout=cancelled&order="+quote(order_id),
            "webhookUrl":base+"/api/billing/webhook",
        },ensure_ascii=False).encode()
        headers={"Content-Type":"application/json","User-Agent":"E-invitation-website/1.0"}
        if BILLING_API_KEY:headers["Authorization"]=f"Bearer {BILLING_API_KEY}"
        with connect() as db:
            db.execute("INSERT INTO billing_orders(id,user_id,plan,status,provider,amount_minor,currency,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(order_id,user["id"],plan,"pending",BILLING_PROVIDER_NAME,amount_minor,BILLING_CURRENCY,now,now))
        try:
            request=urllib.request.Request(BILLING_CHECKOUT_ENDPOINT,data=payload,headers=headers,method="POST")
            with urllib.request.urlopen(request,timeout=20) as response:result=json.loads(response.read(1_000_000) or b"{}")
            url=str(result.get("url") or result.get("checkoutUrl") or result.get("checkout_url") or "")
            if not re.match(r"^https://",url,re.I):raise ValueError("Billing provider returned an invalid checkout URL")
            provider_session=str(result.get("sessionId") or result.get("session_id") or "")[:300]
            with connect() as db:db.execute("UPDATE billing_orders SET provider_session_id=?,updated_at=? WHERE id=?",(provider_session,int(time.time()*1000),order_id))
            self.audit("billing.checkout_started","billing_order",order_id,{"plan":plan,"amountMinor":amount_minor,"currency":BILLING_CURRENCY})
            return self.json(200,{"url":url,"plan":plan,"orderId":order_id})
        except urllib.error.HTTPError as exc:
            with connect() as db:db.execute("UPDATE billing_orders SET status='failed',updated_at=? WHERE id=?",(int(time.time()*1000),order_id))
            try:message=json.loads(exc.read() or b"{}").get("error")
            except Exception:message=None
            return self.json(502,{"error":message or "Billing provider checkout failed"})
        except Exception as exc:
            with connect() as db:db.execute("UPDATE billing_orders SET status='failed',updated_at=? WHERE id=?",(int(time.time()*1000),order_id))
            if JSON_LOGS:print(json.dumps({"level":"warning","event":"billing_checkout_failed","orderId":order_id,"message":str(exc)[:300]}),flush=True)
            return self.json(502,{"error":"Billing provider checkout failed"})

    def billing_webhook(self):
        if not BILLING_WEBHOOK_SECRET:return self.json(503,{"error":"Billing webhook is not configured"})
        size=int(self.headers.get("Content-Length","0"));
        if size<=0 or size>500_000:raise ValueError("Invalid webhook payload")
        raw=self.rfile.read(size);signature=self.headers.get("X-EInvite-Signature","").strip().lower()
        expected=hmac.new(BILLING_WEBHOOK_SECRET.encode(),raw,hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature,expected):return self.json(401,{"error":"Invalid webhook signature"})
        data=json.loads(raw or b"{}");event=str(data.get("type","")).lower();payload=data.get("data") if isinstance(data.get("data"),dict) else data
        event_id=str(data.get("id") or payload.get("eventId") or hashlib.sha256(raw).hexdigest())[:200]
        payload_hash=hashlib.sha256(raw).hexdigest();now=int(time.time()*1000)
        with connect() as db:
            existing=db.execute("SELECT processed_at,payload_hash FROM billing_events WHERE id=?",(event_id,)).fetchone()
            if existing:
                if existing["payload_hash"]!=payload_hash:return self.json(409,{"error":"Billing event identifier was reused with a different payload"})
                if existing["processed_at"] is not None:return self.json(200,{"received":True,"duplicate":True})
            else:db.execute("INSERT INTO billing_events(id,event_type,payload_hash,received_at) VALUES(?,?,?,?)",(event_id,event,payload_hash,now))
        user_id=str(payload.get("userId","") or "");email=str(payload.get("email","") or "").strip().lower();plan=str(payload.get("plan","") or "free").lower()
        order_id=str(payload.get("orderId","") or "")[:200]
        paid_events={"checkout.completed","payment.completed","payment.succeeded"}
        active_events={"subscription.updated","subscription.created"}
        if event in {"subscription.cancelled","subscription.canceled"}:plan="free"
        if event not in paid_events|active_events|{"subscription.cancelled","subscription.canceled"}:
            with connect() as db:db.execute("UPDATE billing_events SET processed_at=? WHERE id=?",(now,event_id))
            return self.json(202,{"received":True,"ignored":True})
        if plan not in PLAN_LIMITS:raise ValueError("Unsupported plan")
        with connect() as db:
            if event in paid_events:
                if not order_id:return self.json(400,{"error":"Paid checkout event is missing orderId"})
                order=db.execute("SELECT * FROM billing_orders WHERE id=?",(order_id,)).fetchone()
                if not order:return self.json(202,{"received":True,"matched":False})
                event_amount=int(payload.get("amountMinor",order["amount_minor"]))
                event_currency=str(payload.get("currency",order["currency"])).upper()
                if plan!=order["plan"] or event_amount!=order["amount_minor"] or event_currency!=order["currency"]:
                    return self.json(409,{"error":"Paid checkout details do not match the original order"})
                user_id=order["user_id"]
            row=db.execute("SELECT id FROM users WHERE id=? OR email=? LIMIT 1",(user_id,email)).fetchone()
            if not row:return self.json(202,{"received":True,"matched":False})
            db.execute("UPDATE users SET plan=? WHERE id=?",(plan,row["id"]))
            if order_id:db.execute("UPDATE billing_orders SET status='paid',paid_at=?,updated_at=? WHERE id=?",(now,now,order_id))
            db.execute("UPDATE billing_events SET processed_at=? WHERE id=?",(now,event_id))
        self.audit("billing.plan_changed","billing_order",order_id,{"event":event,"plan":plan,"eventId":event_id},user_id=row["id"])
        self.json(200,{"received":True,"plan":plan})

    def admin_system_metrics(self):
        user=self.require_role("admin")
        if not user:return
        with connect() as db:
            metrics={
                "users":db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
                "invitations":db.execute("SELECT COUNT(*) c FROM invitations").fetchone()["c"],
                "publications":db.execute("SELECT COUNT(*) c FROM publications").fetchone()["c"],
                "rsvps":db.execute("SELECT COUNT(*) c FROM rsvps").fetchone()["c"],
                "assets":db.execute("SELECT COUNT(*) c FROM assets").fetchone()["c"],
                "assetBytes":db.execute("SELECT COALESCE(SUM(size),0) c FROM assets").fetchone()["c"],
            }
        metrics.update({"uptimeSeconds":int(time.time()-STARTED_AT),"database":DATABASE_KIND,"storage":"object" if object_storage_enabled() else "local","redis":bool(redis_client()),"aiConfigured":bool(AI_ENDPOINT),"smtpConfigured":bool(platform_env("EINVITE_SMTP_HOST","").strip()),"billingWebhookConfigured":bool(BILLING_WEBHOOK_SECRET),"billingCheckoutConfigured":bool(BILLING_CHECKOUT_ENDPOINT)})
        self.json(200,metrics)

    def admin_ai_providers(self):
        user=self.require_role("admin")
        if not user:return
        try:
            service=get_ai_agent_service()
            payload=service.admin_local_provider_status((str(ROOT),))
            self.json(200,payload)
        except AgentServiceError as exc:self.json(exc.status,exc.payload())
        except Exception:self.json(503,{"error":"AI provider status is temporarily unavailable","code":"ai_provider_status_unavailable"})

    def admin_overview(self):
        user=self.require_role("admin")
        if not user:return
        with connect() as db:
            counts={
                "users":db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
                "invitations":db.execute("SELECT COUNT(*) c FROM invitations").fetchone()["c"],
                "publishedInvitations":db.execute("SELECT COUNT(*) c FROM invitations WHERE is_published=1").fetchone()["c"],
                "templates":db.execute("SELECT COUNT(*) c FROM user_templates").fetchone()["c"],
                "marketplaceTemplates":db.execute("SELECT COUNT(*) c FROM user_templates WHERE visibility='public' AND marketplace_status='approved'").fetchone()["c"],
                "rsvps":db.execute("SELECT COUNT(*) c FROM rsvps").fetchone()["c"],
                "assets":db.execute("SELECT COUNT(*) c FROM assets").fetchone()["c"],
            }
        self.json(200,counts)

    def admin_users(self):
        user=self.require_role("admin")
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT u.id,u.email,u.role,u.plan,u.upload_enabled,u.created_at,(SELECT COUNT(*) FROM invitations i WHERE i.owner_id=u.id) invitation_count,(SELECT COUNT(*) FROM user_templates t WHERE t.owner_id=u.id) template_count FROM users u ORDER BY u.created_at DESC LIMIT 1000").fetchall()
        self.json(200,[{"id":r["id"],"email":r["email"],"role":r["role"],"plan":r["plan"],"uploadEnabled":bool(r["upload_enabled"]),"createdAt":r["created_at"],"invitationCount":r["invitation_count"],"templateCount":r["template_count"]} for r in rows])

    def admin_templates(self):
        user=self.require_role("admin")
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT t.*,u.email owner_email FROM user_templates t JOIN users u ON u.id=t.owner_id ORDER BY t.updated_at DESC LIMIT 1000").fetchall()
        self.json(200,[{**self.template_payload(r),"ownerEmail":r["owner_email"]} for r in rows])

    def admin_invitations(self):
        user=self.require_role("admin")
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT i.id,i.slug,i.updated_at,i.archived,i.views,i.access_mode,i.is_published,u.email owner_email,i.draft_json FROM invitations i LEFT JOIN users u ON u.id=i.owner_id ORDER BY i.updated_at DESC LIMIT 1000").fetchall()
        result=[]
        for r in rows:
            try:document=json.loads(r["draft_json"]);title=document.get("fields",{}).get("names") or "Untitled invitation"
            except Exception:title="Untitled invitation"
            result.append({"id":r["id"],"slug":r["slug"],"title":title,"ownerEmail":r["owner_email"],"published":bool(r["is_published"]),"archived":bool(r["archived"]),"views":r["views"],"accessMode":r["access_mode"],"updatedAt":r["updated_at"]})
        self.json(200,result)

    def admin_update_user_plan(self,user_id):
        admin=self.require_role("admin")
        if not admin:return
        data=self.body(20_000);plan=str(data.get("plan","free"))
        if plan not in {"free","creator","studio"}:raise ValueError("Invalid account plan")
        with connect() as db:changed=db.execute("UPDATE users SET plan=? WHERE id=?",(plan,user_id)).rowcount
        self.json(200 if changed else 404,{"updated":bool(changed),"plan":plan})

    def admin_update_user_role(self,user_id):
        admin=self.require_role("admin")
        if not admin:return
        data=self.body(20_000);role=str(data.get("role",""))
        if role not in {"customer","designer","admin"}:raise ValueError("Invalid account role")
        if user_id==admin["id"] and role!="admin":raise ValueError("You cannot remove your own administrator role")
        with connect() as db:changed=db.execute("UPDATE users SET role=? WHERE id=?",(role,user_id)).rowcount
        self.json(200 if changed else 404,{"updated":bool(changed),"role":role})

    def admin_update_user_upload_permission(self,user_id):
        admin=self.require_role("admin")
        if not admin:return
        data=self.body(20_000)
        if not isinstance(data.get("enabled"),bool):raise ValueError("Upload permission must be true or false")
        enabled=1 if data["enabled"] else 0
        with connect() as db:changed=db.execute("UPDATE users SET upload_enabled=? WHERE id=?",(enabled,user_id)).rowcount
        if changed:self.audit("account.upload_permission_changed","user",user_id,{"enabled":bool(enabled)},user_id=admin["id"])
        self.json(200 if changed else 404,{"updated":bool(changed),"uploadEnabled":bool(enabled)})

    def admin_update_template_visibility(self,template_id):
        admin=self.require_role("admin")
        if not admin:return
        data=self.body(20_000);visibility=str(data.get("visibility","private"))
        if visibility not in {"private","public"}:raise ValueError("Invalid template visibility")
        now=int(time.time()*1000);published_at=now if visibility=="public" else None
        with connect() as db:changed=db.execute("UPDATE user_templates SET visibility=?,published_at=?,marketplace_status=?,updated_at=? WHERE id=?",(visibility,published_at,"approved" if visibility=="public" else "rejected",now,template_id)).rowcount
        self.json(200 if changed else 404,{"updated":bool(changed),"visibility":visibility})

    def admin_update_invitation_published(self,invite_id):
        admin=self.require_role("admin")
        if not admin:return
        data=self.body(20_000);published=1 if data.get("published") else 0;now=int(time.time()*1000)
        with connect() as db:changed=db.execute("UPDATE invitations SET is_published=?,updated_at=? WHERE id=?",(published,now,invite_id)).rowcount
        self.json(200 if changed else 404,{"updated":bool(changed),"published":bool(published)})

    def _create_auth_token(self,user_id,kind,lifetime_ms):
        token=secrets.token_urlsafe(36);now=int(time.time()*1000);token_hash=hashlib.sha256(token.encode()).hexdigest()
        with connect() as db:
            db.execute("DELETE FROM auth_tokens WHERE user_id=? AND kind=?",(user_id,kind))
            db.execute("INSERT INTO auth_tokens(token_hash,user_id,kind,expires_at,created_at) VALUES(?,?,?,?,?)",(token_hash,user_id,kind,now+lifetime_ms,now))
        return token

    def request_password_reset(self):
        if not self.rate_limit(f"password-reset:{self.client_address[0]}",8,3600):return
        data=self.body(30_000);email=str(data.get("email","")).strip().lower()[:254];sent=False;dev_token=None
        if not self.bot_protection_ok("password-reset",data.get("botToken","")):return self.json(403,{"error":"Password-reset verification failed"})
        with connect() as db:row=db.execute("SELECT id,email FROM users WHERE email=?",(email,)).fetchone()
        if row:
            token=self._create_auth_token(row["id"],"password-reset",30*60*1000);url=auth_action_url("/reset.html",token)
            try:sent=send_platform_email(row["email"],"Reset your E-invitation-website password",f"A password reset was requested for your E-invitation-website account.\n\nOpen this link within 30 minutes:\n{url}\n\nIf you did not request this, you can ignore this message.")
            except Exception as exc:print(f"Password-reset email delivery failed: {exc}",flush=True)
            if platform_env("EINVITE_DEV_AUTH_TOKENS","").lower() in {"1","true","yes"}:dev_token=token
        # Production responses must not reveal whether an account exists or
        # whether a delivery provider accepted mail for a particular address.
        payload={"accepted":True,"sent":True if PRODUCTION_MODE else bool(sent)}
        if dev_token:payload["devToken"]=dev_token
        self.json(200,payload)

    def confirm_password_reset(self):
        if not self.rate_limit(f"password-reset-confirm:{self.client_address[0]}",20,3600):return
        data=self.body(50_000);token=str(data.get("token","")).strip();new=str(data.get("newPassword",""))
        if len(new)<8 or len(new)>200:raise ValueError("New password must be 8 to 200 characters")
        token_hash=hashlib.sha256(token.encode()).hexdigest();now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT user_id FROM auth_tokens WHERE token_hash=? AND kind='password-reset' AND expires_at>?",(token_hash,now)).fetchone()
            if not row:return self.json(400,{"error":"This password-reset link is invalid or expired"})
            hashed,salt,algo=account_hash_password(new);db.execute("UPDATE users SET password_hash=?,salt=?,password_algo=? WHERE id=?",(hashed,salt,algo,row["user_id"]));db.execute("DELETE FROM sessions WHERE user_id=?",(row["user_id"],));db.execute("DELETE FROM auth_tokens WHERE user_id=? AND kind='password-reset'",(row["user_id"],));account=db.execute("SELECT email FROM users WHERE id=?",(row["user_id"],)).fetchone()
        if account:security_notification(account["email"],"Your password was reset","Your E-invitation-website password was reset and existing sessions were signed out.")
        self.audit("password.reset","user",row["user_id"],user_id=row["user_id"])
        self.json(200,{"changed":True})

    def request_email_verification(self):
        user=self.require_user()
        if not user:return
        if user["email_verified"]:return self.json(200,{"verified":True,"sent":False})
        if not self.rate_limit(f"verify-email:{user['id']}",6,3600):return
        token=self._create_auth_token(user["id"],"email-verification",24*60*60*1000);url=auth_action_url("/verify.html",token);sent=False
        try:sent=send_platform_email(user["email"],"Verify your E-invitation-website email",f"Verify your E-invitation-website email address by opening this link within 24 hours:\n\n{url}")
        except Exception as exc:print(f"Verification email delivery failed: {exc}",flush=True)
        payload={"verified":False,"sent":bool(sent)}
        if platform_env("EINVITE_DEV_AUTH_TOKENS","").lower() in {"1","true","yes"}:payload["devToken"]=token
        self.json(200,payload)

    def confirm_email_verification(self):
        data=self.body(30_000);token=str(data.get("token","")).strip();token_hash=hashlib.sha256(token.encode()).hexdigest();now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT user_id FROM auth_tokens WHERE token_hash=? AND kind='email-verification' AND expires_at>?",(token_hash,now)).fetchone()
            if not row:return self.json(400,{"error":"This verification link is invalid or expired"})
            account=db.execute("SELECT email,role FROM users WHERE id=? AND deleted_at IS NULL",(row["user_id"],)).fetchone()
            admin_email=platform_env("EINVITE_ADMIN_EMAIL","").strip().lower();promote=bool(account and admin_email and account["email"]==admin_email)
            if promote:db.execute("UPDATE users SET email_verified=1,role='admin',plan='studio' WHERE id=?",(row["user_id"],))
            else:db.execute("UPDATE users SET email_verified=1 WHERE id=?",(row["user_id"],))
            db.execute("DELETE FROM auth_tokens WHERE user_id=? AND kind='email-verification'",(row["user_id"],))
        self.audit("email.verified","user",row["user_id"],{"administratorPromoted":promote},user_id=row["user_id"])
        self.json(200,{"verified":True,"role":"admin" if promote else (account["role"] if account else "customer")})

    def change_password(self):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);current=str(data.get("currentPassword",""));new=str(data.get("newPassword",""))
        if len(new)<8 or len(new)>200:raise ValueError("New password must be 8 to 200 characters")
        current_token=self.auth_token();current_token_hash=hashlib.sha256(current_token.encode()).hexdigest() if current_token else ""
        with connect() as db:
            row=db.execute("SELECT password_hash,salt,password_algo FROM users WHERE id=?",(user["id"],)).fetchone()
            valid,_=account_verify_password(current,row["password_hash"],row["salt"],row["password_algo"] if row else "") if row else (False,False)
            if not valid:return self.json(401,{"error":"Current password is incorrect"})
            hashed,salt,algo=account_hash_password(new);db.execute("UPDATE users SET password_hash=?,salt=?,password_algo=? WHERE id=?",(hashed,salt,algo,user["id"]))
            if current_token_hash:db.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?",(user["id"],current_token_hash))
        self.audit("password.changed","user",user["id"])
        security_notification(user["email"],"Your password was changed",f"Your password was changed from IP {self.client_ip()}.")
        self.json(200,{"changed":True})

    def plan_usage(self, db, user):
        plan=user["plan"] if user["plan"] in PLAN_LIMITS else "free"
        invitations=db.execute("SELECT COUNT(*) c FROM invitations WHERE owner_id=? AND archived=0",(user["id"],)).fetchone()["c"]
        templates=db.execute("SELECT COUNT(*) c FROM user_templates WHERE owner_id=?",(user["id"],)).fetchone()["c"]
        storage=db.execute("SELECT COALESCE(SUM(size),0) total FROM stored_objects WHERE owner_id=? AND processing_state='ready' AND ref_count>0",(user["id"],)).fetchone()["total"]
        return plan,{"invitations":int(invitations or 0),"templates":int(templates or 0),"storageBytes":int(storage or 0),"bandwidthBytes30d":bandwidth_usage_30d(user["id"],db)},PLAN_LIMITS[plan]

    def require_plan_capacity(self, user, kind, additional=1):
        if kind=="storageBytes" and REQUIRE_VERIFIED_EMAIL and str(user["plan"] or "free")!="free" and not bool(user["email_verified"]):
            self.json(403,{"error":"Verify your email before using paid storage capacity","code":"email_verification_required"});return False
        if not PLAN_LIMITS_ENFORCED:return True
        with connect() as db:plan,usage,limits=self.plan_usage(db,user)
        if usage[kind]+additional>limits[kind]:
            label={"invitations":"active invitation","templates":"reusable template","storageBytes":"material storage","bandwidthBytes30d":"30-day media bandwidth"}.get(kind,kind)
            self.json(403,{"error":f"Your {plan} plan has reached its {label} limit","code":"plan_limit_reached","plan":plan,"usage":usage,"limits":limits})
            return False
        return True

    def account_usage(self):
        user=self.require_user()
        if not user:return
        with connect() as db:plan,usage,limits=self.plan_usage(db,user)
        self.json(200,{"plan":plan,"usage":usage,"limits":limits,"enforced":PLAN_LIMITS_ENFORCED})

    def export_account(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            invitations=[dict(r) for r in db.execute("SELECT id,slug,draft_json,updated_at,archived,views,access_mode,is_published FROM invitations WHERE owner_id=? ORDER BY updated_at DESC",(user["id"],)).fetchall()]
            invite_ids=[r["id"] for r in invitations]
            def rows_for(table,columns="*"):
                if not invite_ids:return []
                q=','.join('?' for _ in invite_ids);return [dict(r) for r in db.execute(f"SELECT {columns} FROM {table} WHERE invitation_id IN ({q})",invite_ids).fetchall()]
            publications=rows_for("publications");rsvps=rows_for("rsvps");guests=rows_for("guests");wishes=rows_for("guest_messages");assets=rows_for("assets","id,invitation_id,name,mime,path,size,created_at,folder,tags_json,favorite")
            templates=[dict(r) for r in db.execute("SELECT id,name,category,document_json,description,tags_json,favorite,current_version,visibility,published_at,created_at,updated_at FROM user_templates WHERE owner_id=?",(user["id"],)).fetchall()]
            page_templates=[dict(r) for r in db.execute("SELECT * FROM user_page_templates WHERE owner_id=?",(user["id"],)).fetchall()]
            components=[dict(r) for r in db.execute("SELECT * FROM user_components WHERE owner_id=?",(user["id"],)).fetchall()]
            studio_resources=[dict(r) for r in db.execute("SELECT * FROM studio_resources WHERE owner_id=?",(user["id"],)).fetchall()]
            studio_releases=[dict(r) for r in db.execute("SELECT * FROM studio_releases WHERE owner_id=?",(user["id"],)).fetchall()]
            studio_release_pins=[dict(r) for r in db.execute("SELECT p.* FROM invitation_studio_release_pins p JOIN invitations i ON i.id=p.invitation_id WHERE i.owner_id=?",(user["id"],)).fetchall()]
            studio_governance=db.execute("SELECT policy_json,updated_at FROM studio_governance WHERE owner_id=?",(user["id"],)).fetchone()
            studio_backup_policy=db.execute("SELECT * FROM studio_backup_policies WHERE owner_id=?",(user["id"],)).fetchone()
            studio_bulk_jobs=[dict(r) for r in db.execute("SELECT * FROM studio_bulk_jobs WHERE owner_id=? ORDER BY created_at DESC LIMIT 100",(user["id"],)).fetchall()]
        for collection,key in ((invitations,"draft_json"),(publications,"document_json"),(templates,"document_json"),(page_templates,"page_json"),(components,"payload_json")):
            for item in collection:
                if key in item:
                    try:item[key[:-5] if key.endswith('_json') else key]=json.loads(item.pop(key))
                    except Exception:pass
        for item in rsvps:
            try:item["answers"]=json.loads(item.pop("answers_json","{}") or "{}")
            except Exception:item["answers"]={}
        for item in studio_resources:
            for key in ("payload_json","governance_json"):
                try:item[key[:-5] if key.endswith("_json") else key]=json.loads(item.pop(key) or "{}")
                except Exception:item[key[:-5] if key.endswith("_json") else key]={}
        for item in studio_releases:
            try:item["manifest"]=json.loads(item.pop("manifest_json") or "[]")
            except Exception:item["manifest"]=[]
        for item in studio_bulk_jobs:
            for key in ("selection_json","result_json"):
                try:item[key[:-5]]=json.loads(item.pop(key) or "{}")
                except Exception:item[key[:-5]]={}
        governance_export={}
        if studio_governance:
            try:governance_export={"policy":json.loads(studio_governance["policy_json"] or "{}"),"updatedAt":studio_governance["updated_at"]}
            except Exception:governance_export={}
        self.json(200,{"exportedAt":int(time.time()*1000),"account":{"id":user["id"],"email":user["email"],"role":user["role"],"plan":user["plan"],"emailVerified":bool(user["email_verified"]),"uploadEnabled":bool(user["upload_enabled"] if "upload_enabled" in user.keys() else 1)},"invitations":invitations,"publications":publications,"rsvps":rsvps,"guests":guests,"wishes":wishes,"assets":assets,"templates":templates,"pageTemplates":page_templates,"components":components,"studioResources":studio_resources,"studioReleases":studio_releases,"studioReleasePins":studio_release_pins,"studioGovernance":governance_export,"studioBackupPolicy":dict(studio_backup_policy) if studio_backup_policy else {},"studioBulkJobs":studio_bulk_jobs})

    def register(self):
        if not self.rate_limit(f"register:{self.client_address[0]}",10,600): return
        data=self.body(100_000); email=str(data.get("email","")).strip().lower()[:254]; password=str(data.get("password",""))
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):raise ValueError("Valid email required")
        if len(password)<8 or len(password)>200:raise ValueError("Password must be 8 to 200 characters")
        if not self.bot_protection_ok("register",data.get("botToken","")):return self.json(403,{"error":"Registration verification failed"})
        user_id=str(uuid.uuid4()); hashed,salt,algo=account_hash_password(password); now=int(time.time()*1000);admin_email=platform_env("EINVITE_ADMIN_EMAIL","").strip().lower()
        # A public registrant must prove control of the configured administrator
        # email before receiving administrator authority. Local loopback bootstrap
        # remains available for the bundled offline test/development workflow.
        local_admin=bool(admin_email and email==admin_email and ALLOW_LOCAL_ADMIN_BOOTSTRAP and is_loopback_address(self.client_ip()))
        role="admin" if local_admin else "customer"
        try:
            with connect() as db: db.execute("INSERT INTO users(id,email,password_hash,salt,password_algo,created_at,role,email_verified,plan) VALUES(?,?,?,?,?,?,?,0,?)",(user_id,email,hashed,salt,algo,now,role,"studio" if role=="admin" else "free"))
        except Exception as exc:
            if isinstance(exc,sqlite3.IntegrityError) or exc.__class__.__name__ in {"UniqueViolation","IntegrityError"}:return self.json(409,{"error":"An account with this email already exists"})
            raise
        ensure_personal_workspace(connect,user_id)
        self.create_session(user_id,email,role)
    def login(self):
        if not self.rate_limit(f"login:{self.client_address[0]}",30,600): return
        data=self.body(100_000); email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
        if len(password)>200:return self.json(401,{"error":"Incorrect email or password"})
        with connect() as db: row=db.execute("SELECT * FROM users WHERE email=? AND deleted_at IS NULL",(email,)).fetchone()
        valid,rehash=account_verify_password(password,row["password_hash"],row["salt"],row["password_algo"] if row and "password_algo" in row.keys() else "") if row else (False,False)
        if not row or not valid:return self.json(401,{"error":"Incorrect email or password"})
        if rehash:
            hashed,salt,algo=account_hash_password(password)
            with connect() as db:db.execute("UPDATE users SET password_hash=?,salt=?,password_algo=? WHERE id=?",(hashed,salt,algo,row["id"]))
        if bool(row["mfa_enabled"] if "mfa_enabled" in row.keys() else 0):
            token=self._create_auth_token(row["id"],"mfa-login",5*60*1000)
            self.audit("login.mfa_challenge","user",row["id"],user_id=row["id"])
            return self.json(202,{"mfaRequired":True,"mfaToken":token,"methods":["totp"]})
        with connect() as db:known_device=db.execute("SELECT 1 FROM sessions WHERE user_id=? AND (ip_address=? OR user_agent=?) LIMIT 1",(row["id"],self.client_ip(),str(self.headers.get("User-Agent") or "")[:500])).fetchone()
        self.audit("login.success","user",row["id"],user_id=row["id"])
        if not known_device:security_notification(row["email"],"New sign-in to your E-invitation account",f"A new sign-in was detected from IP {self.client_ip()} using {str(self.headers.get('User-Agent') or 'an unknown browser')[:180]}.")
        self.create_session(row["id"],row["email"],row["role"] if "role" in row.keys() else "customer",bool(row["email_verified"] if "email_verified" in row.keys() else 0))
    def create_session(self,user_id,email,role="customer",email_verified=False):
        token=secrets.token_urlsafe(32);csrf=new_csrf_token();now=int(time.time()*1000);expires=now+30*24*60*60*1000;session_id=str(uuid.uuid4())
        user_agent=str(self.headers.get("User-Agent") or "")[:500];device_name=(user_agent.split(" ",1)[0] or "Browser")[:80]
        with connect() as db:
            row=db.execute("SELECT email_verified,plan,upload_enabled,mfa_enabled FROM users WHERE id=?",(user_id,)).fetchone()
            if email_verified is False:email_verified=bool(row["email_verified"]) if row else False
            plan=row["plan"] if row and "plan" in row.keys() else "free"
            db.execute("INSERT INTO sessions(token_hash,id,user_id,expires_at,created_at,user_agent,ip_address,last_seen_at,device_name,csrf_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),session_id,user_id,expires,now,user_agent,self.client_ip(),now,device_name,hashlib.sha256(csrf.encode()).hexdigest()))
        cookie=f"{SESSION_COOKIE_NAME}={token}; Path=/; Max-Age={30*24*60*60}; HttpOnly; SameSite=Lax"
        csrf_cookie=f"einvite_csrf={csrf}; Path=/; Max-Age={30*24*60*60}; SameSite=Lax"
        if COOKIE_SECURE:cookie+="; Secure";csrf_cookie+="; Secure"
        payload={"user":{"id":user_id,"email":email,"role":role,"emailVerified":bool(email_verified),"plan":plan,"uploadEnabled":bool(row["upload_enabled"] if row and "upload_enabled" in row.keys() else 1),"mfaEnabled":bool(row["mfa_enabled"] if row and "mfa_enabled" in row.keys() else 0)},"expiresAt":expires,"csrfToken":csrf}
        if DEV_AUTH_TOKENS_ENABLED:payload["token"]=token
        self._session_replaced=True
        self.json(201,payload,{"Set-Cookie":[cookie,csrf_cookie]})

    def logout(self):
        user=self.user();tokens=self.auth_tokens()
        if tokens:
            with connect() as db:
                for token in tokens:db.execute("DELETE FROM sessions WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))
        if user:self.audit("logout","user",user["id"],user_id=user["id"])
        cookie=f"{SESSION_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax";csrf_cookie="einvite_csrf=; Path=/; Max-Age=0; SameSite=Lax"
        if COOKIE_SECURE:cookie+="; Secure";csrf_cookie+="; Secure"
        self.json(200,{"signedOut":True},{"Set-Cookie":[cookie,csrf_cookie]})

    def complete_mfa_login(self):
        if not self.rate_limit(f"mfa-login:{self.client_ip()}",20,600):return
        data=self.body(30_000);token=str(data.get("mfaToken","")).strip();code=str(data.get("code","")).strip();token_hash=hashlib.sha256(token.encode()).hexdigest();now=int(time.time()*1000)
        with connect() as db:
            auth=db.execute("SELECT user_id FROM auth_tokens WHERE token_hash=? AND kind='mfa-login' AND expires_at>?",(token_hash,now)).fetchone()
            if not auth:return self.json(400,{"error":"MFA challenge expired or invalid"})
            row=db.execute("SELECT id,email,role,email_verified,plan,mfa_secret,mfa_enabled FROM users WHERE id=? AND deleted_at IS NULL",(auth["user_id"],)).fetchone()
            if not row or not row["mfa_enabled"] or not row["mfa_secret"] or not verify_totp(row["mfa_secret"],code):return self.json(401,{"error":"Incorrect authentication code"})
            db.execute("DELETE FROM auth_tokens WHERE user_id=? AND kind='mfa-login'",(row["id"],))
        self.audit("login.mfa_success","user",row["id"],user_id=row["id"]);self.create_session(row["id"],row["email"],row["role"],bool(row["email_verified"]))

    def get_studio_profile(self):
        user=self.require_user()
        if not user:return
        with connect() as db:row=db.execute("SELECT studio_name,white_label_json,plan FROM users WHERE id=?",(user["id"],)).fetchone()
        try:white=json.loads(row["white_label_json"] or "{}") if row else {}
        except Exception:white={}
        self.json(200,{"studioName":row["studio_name"] or "" if row else "","whiteLabel":white,"plan":row["plan"] if row else "free"})

    def update_studio_profile(self):
        user=self.require_user()
        if not user:return
        data=self.body(100_000);name=str(data.get("studioName","")).strip()[:120];white=data.get("whiteLabel") if isinstance(data.get("whiteLabel"),dict) else {}
        allowed={
            "logo":str(white.get("logo","")).strip()[:1000],
            "primaryColor":str(white.get("primaryColor","")).strip()[:20],
            "accentColor":str(white.get("accentColor","")).strip()[:20],
            "supportEmail":str(white.get("supportEmail","")).strip()[:254],
            "website":str(white.get("website","")).strip()[:1000],
            "hidePlatformBrand":bool(white.get("hidePlatformBrand",False)),
        }
        for key in ("primaryColor","accentColor"):
            if allowed[key] and not re.fullmatch(r"#[0-9a-fA-F]{6}",allowed[key]):raise ValueError("Studio colors must use six-digit hex values")
        for key in ("logo","website"):
            if allowed[key] and not (allowed[key].startswith("/uploads/") or allowed[key].startswith("/api/media/") or re.match(r"^https://",allowed[key],re.I)):raise ValueError("Studio URLs must use HTTPS or platform-managed media")
        if allowed["supportEmail"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",allowed["supportEmail"]):raise ValueError("Invalid studio support email")
        with connect() as db:db.execute("UPDATE users SET studio_name=?,white_label_json=? WHERE id=?",(name,json.dumps(allowed,ensure_ascii=False),user["id"]))
        self.audit("studio.profile_updated","user",user["id"],{"studioName":name,"whiteLabel":{k:v for k,v in allowed.items() if k!="supportEmail"}})
        self.json(200,{"studioName":name,"whiteLabel":allowed})

    def security_overview(self):
        user=self.require_user()
        if not user:return
        current_hash=hashlib.sha256((self.auth_token() or "").encode()).hexdigest()
        with connect() as db:
            row=db.execute("SELECT password_algo,mfa_enabled,created_at,email_verified,privacy_json FROM users WHERE id=?",(user["id"],)).fetchone()
            passkeys=db.execute("SELECT COUNT(*) c FROM passkeys WHERE user_id=?",(user["id"],)).fetchone()["c"]
            sessions=db.execute("SELECT COUNT(*) c FROM sessions WHERE user_id=? AND expires_at>?",(user["id"],int(time.time()*1000))).fetchone()["c"]
        try:privacy=json.loads(row["privacy_json"] or "{}")
        except Exception:privacy={}
        self.json(200,{"passwordAlgorithm":row["password_algo"],"argon2Available":ARGON2_AVAILABLE,"mfaEnabled":bool(row["mfa_enabled"]),"passkeyCount":int(passkeys or 0),"activeSessions":int(sessions or 0),"emailVerified":bool(row["email_verified"]),"privacy":privacy,"currentSessionHash":current_hash[:12]})

    def list_sessions(self):
        user=self.require_user()
        if not user:return
        token_hash=hashlib.sha256((self.auth_token() or "").encode()).hexdigest();now=int(time.time()*1000)
        with connect() as db:rows=db.execute("SELECT id,token_hash,created_at,last_seen_at,expires_at,user_agent,ip_address,device_name FROM sessions WHERE user_id=? AND expires_at>? ORDER BY last_seen_at DESC,created_at DESC",(user["id"],now)).fetchall()
        self.json(200,[{"id":r["id"] or r["token_hash"],"current":hmac.compare_digest(r["token_hash"],token_hash),"createdAt":r["created_at"],"lastSeenAt":r["last_seen_at"],"expiresAt":r["expires_at"],"deviceName":r["device_name"] or "Browser","userAgent":r["user_agent"],"ipAddress":r["ip_address"]} for r in rows])

    def revoke_session(self,session_id):
        user=self.require_user()
        if not user:return
        current=hashlib.sha256((self.auth_token() or "").encode()).hexdigest()
        with connect() as db:
            row=db.execute("SELECT token_hash FROM sessions WHERE user_id=? AND id=?",(user["id"],session_id)).fetchone()
            if not row:return self.json(404,{"error":"Session not found"})
            db.execute("DELETE FROM sessions WHERE user_id=? AND id=?",(user["id"],session_id))
        self.audit("session.revoked","session",session_id,{"current":hmac.compare_digest(row["token_hash"],current)})
        self.json(200,{"revoked":True,"current":hmac.compare_digest(row["token_hash"],current)})

    def revoke_all_sessions(self):
        user=self.require_user()
        if not user:return
        current=hashlib.sha256((self.auth_token() or "").encode()).hexdigest();keep=bool(self.body(10_000).get("keepCurrent",False))
        with connect() as db:
            if keep:count=db.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?",(user["id"],current)).rowcount
            else:count=db.execute("DELETE FROM sessions WHERE user_id=?",(user["id"],)).rowcount
        self.audit("session.revoke_all","user",user["id"],{"keepCurrent":keep,"count":int(count or 0)})
        self.json(200,{"revoked":int(count or 0),"keptCurrent":keep})

    def mfa_qr_png(self):
        user=self.require_user()
        if not user:return
        with connect() as db:row=db.execute("SELECT mfa_secret FROM users WHERE id=?",(user["id"],)).fetchone()
        if not row or not row["mfa_secret"]:return self.json(404,{"error":"Start authenticator setup first"})
        qr=make_qr_image(otpauth_uri(row["mfa_secret"],user["email"]),8,3)
        if qr is None:return self.json(503,{"error":"QR generation support is not installed"})
        out=io.BytesIO();qr.save(out,"PNG",optimize=True);return self.send_binary(200,out.getvalue(),"image/png","private,max-age=0,no-store","mfa-setup.png")

    def mfa_setup(self):
        user=self.require_user()
        if not user:return
        secret=new_totp_secret()
        with connect() as db:db.execute("UPDATE users SET mfa_secret=?,mfa_enabled=0 WHERE id=?",(secret,user["id"]))
        self.audit("mfa.setup_started","user",user["id"])
        self.json(200,{"secret":secret,"otpauthUri":otpauth_uri(secret,user["email"]),"issuer":PASSKEY_RP_NAME})

    def mfa_enable(self):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);code=str(data.get("code","")).strip()
        with connect() as db:
            row=db.execute("SELECT mfa_secret FROM users WHERE id=?",(user["id"],)).fetchone()
            if not row or not row["mfa_secret"] or not verify_totp(row["mfa_secret"],code):return self.json(400,{"error":"Enter the current 6-digit authenticator code"})
            db.execute("UPDATE users SET mfa_enabled=1 WHERE id=?",(user["id"],))
        self.audit("mfa.enabled","user",user["id"]);self.json(200,{"enabled":True})

    def mfa_disable(self):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);code=str(data.get("code","")).strip()
        with connect() as db:
            row=db.execute("SELECT mfa_secret,mfa_enabled FROM users WHERE id=?",(user["id"],)).fetchone()
            if row and row["mfa_enabled"] and (not row["mfa_secret"] or not verify_totp(row["mfa_secret"],code)):return self.json(400,{"error":"Enter a valid authenticator code"})
            db.execute("UPDATE users SET mfa_enabled=0,mfa_secret=NULL WHERE id=?",(user["id"],))
        self.audit("mfa.disabled","user",user["id"]);self.json(200,{"enabled":False})

    def create_webauthn_challenge(self,user_id,kind,metadata=None):
        challenge=b64url(secrets.token_bytes(32));challenge_id=str(uuid.uuid4());now=int(time.time()*1000)
        with connect() as db:
            db.execute("DELETE FROM auth_challenges WHERE expires_at<=? OR used_at IS NOT NULL",(now,))
            db.execute("INSERT INTO auth_challenges(id,user_id,kind,challenge,metadata_json,expires_at,used_at) VALUES(?,?,?,?,?,?,NULL)",(challenge_id,user_id,kind,challenge,json.dumps(metadata or {}),now+5*60*1000))
        return challenge_id,challenge

    def passkey_register_options(self):
        user=self.require_user()
        if not user:return
        cid,challenge=self.create_webauthn_challenge(user["id"],"passkey-register")
        self.json(200,{"challengeId":cid,"publicKey":{"challenge":challenge,"rp":{"name":PASSKEY_RP_NAME,"id":self.rp_id()},"user":{"id":b64url(user["id"].encode()),"name":user["email"],"displayName":user["email"]},"pubKeyCredParams":[{"type":"public-key","alg":-7}],"timeout":60000,"attestation":"none","authenticatorSelection":{"residentKey":"preferred","userVerification":"preferred"}}})

    def passkey_register_complete(self):
        user=self.require_user()
        if not user:return
        data=self.body(300_000);cid=str(data.get("challengeId","")).strip();credential=data.get("credential") if isinstance(data.get("credential"),dict) else {};response=credential.get("response") if isinstance(credential.get("response"),dict) else {};now=int(time.time()*1000)
        with connect() as db:challenge=db.execute("SELECT * FROM auth_challenges WHERE id=? AND user_id=? AND kind='passkey-register' AND expires_at>? AND used_at IS NULL",(cid,user["id"],now)).fetchone()
        if not challenge:return self.json(400,{"error":"Passkey registration challenge expired"})
        client_raw,_=verify_client_data(response.get("clientDataJSON",""),challenge["challenge"],self.origin_base(),"webauthn.create");parsed=parse_attestation_object(response.get("attestationObject",""));rp_hash=hashlib.sha256(self.rp_id().encode()).digest()
        if not hmac.compare_digest(parsed["authData"][:32],rp_hash):return self.json(400,{"error":"Passkey relying-party mismatch"})
        if not (parsed["authData"][32]&0x01):return self.json(400,{"error":"Passkey registration requires user presence"})
        public_key=cose_ec2_to_pem(parsed["coseKey"]);credential_id=b64url(parsed["credentialId"]);transports=credential.get("transports") if isinstance(credential.get("transports"),list) else [];name=str(data.get("name") or "Passkey")[:80]
        with connect() as db:
            db.execute("INSERT INTO passkeys(id,user_id,credential_id,public_key,sign_count,transports_json,name,created_at,last_used_at) VALUES(?,?,?,?,?,?,?,?,NULL)",(str(uuid.uuid4()),user["id"],credential_id,public_key,parsed["signCount"],json.dumps(transports),name,now));db.execute("UPDATE auth_challenges SET used_at=? WHERE id=?",(now,cid))
        self.audit("passkey.added","user",user["id"],{"name":name});self.json(201,{"registered":True,"credentialId":credential_id,"name":name})

    def passkey_login_options(self):
        if not self.rate_limit(f"passkey-options:{self.client_ip()}",30,600):return
        data=self.body(30_000);email=str(data.get("email","")).strip().lower()
        with connect() as db:
            user=db.execute("SELECT id,email FROM users WHERE email=? AND deleted_at IS NULL",(email,)).fetchone();rows=db.execute("SELECT credential_id,transports_json FROM passkeys WHERE user_id=?",(user["id"],)).fetchall() if user else []
        if not user or not rows:
            # Return an indistinguishable, non-persisted challenge so this public
            # endpoint cannot be used to enumerate registered email addresses.
            dummy_challenge=b64url(secrets.token_bytes(32));dummy_credential=b64url(secrets.token_bytes(32))
            return self.json(200,{"challengeId":str(uuid.uuid4()),"publicKey":{"challenge":dummy_challenge,"rpId":self.rp_id(),"allowCredentials":[{"type":"public-key","id":dummy_credential,"transports":[]}],"timeout":60000,"userVerification":"preferred"}})
        cid,challenge=self.create_webauthn_challenge(user["id"],"passkey-login")
        allow=[]
        for row in rows:
            try:transports=json.loads(row["transports_json"] or "[]")
            except Exception:transports=[]
            allow.append({"type":"public-key","id":row["credential_id"],"transports":transports})
        self.json(200,{"challengeId":cid,"publicKey":{"challenge":challenge,"rpId":self.rp_id(),"allowCredentials":allow,"timeout":60000,"userVerification":"preferred"}})

    def passkey_login_complete(self):
        if not self.rate_limit(f"passkey-login:{self.client_ip()}",30,600):return
        data=self.body(300_000);cid=str(data.get("challengeId","")).strip();credential=data.get("credential") if isinstance(data.get("credential"),dict) else {};response=credential.get("response") if isinstance(credential.get("response"),dict) else {};credential_id=str(credential.get("id","")).strip();now=int(time.time()*1000)
        with connect() as db:
            challenge=db.execute("SELECT * FROM auth_challenges WHERE id=? AND kind='passkey-login' AND expires_at>? AND used_at IS NULL",(cid,now)).fetchone()
            key=db.execute("SELECT p.*,u.email,u.role,u.email_verified FROM passkeys p JOIN users u ON u.id=p.user_id WHERE p.user_id=? AND p.credential_id=? AND u.deleted_at IS NULL",(challenge["user_id"],credential_id)).fetchone() if challenge else None
        if not challenge or not key:return self.json(400,{"error":"Passkey challenge expired or credential is unknown"})
        client_raw,_=verify_client_data(response.get("clientDataJSON",""),challenge["challenge"],self.origin_base(),"webauthn.get");auth_data,sign_count,rp_hash=parse_assertion_auth_data(response.get("authenticatorData",""))
        if not hmac.compare_digest(rp_hash,hashlib.sha256(self.rp_id().encode()).digest()):return self.json(400,{"error":"Passkey relying-party mismatch"})
        if not (auth_data[32]&0x01):return self.json(401,{"error":"Passkey authentication requires user presence"})
        signed=auth_data+hashlib.sha256(client_raw).digest();signature=b64url_decode(response.get("signature",""))
        if not verify_es256_signature(key["public_key"],signature,signed):return self.json(401,{"error":"Passkey signature verification failed"})
        if int(key["sign_count"] or 0)>0 and sign_count>0 and sign_count<=int(key["sign_count"]):return self.json(401,{"error":"Passkey sign counter did not advance"})
        with connect() as db:db.execute("UPDATE passkeys SET sign_count=?,last_used_at=? WHERE id=?",(max(sign_count,int(key["sign_count"] or 0)),now,key["id"]));db.execute("UPDATE auth_challenges SET used_at=? WHERE id=?",(now,cid))
        self.audit("login.passkey_success","user",key["user_id"],user_id=key["user_id"]);self.create_session(key["user_id"],key["email"],key["role"],bool(key["email_verified"]))

    def list_passkeys(self):
        user=self.require_user()
        if not user:return
        with connect() as db:rows=db.execute("SELECT id,name,created_at,last_used_at FROM passkeys WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall()
        self.json(200,[{"id":r["id"],"name":r["name"],"createdAt":r["created_at"],"lastUsedAt":r["last_used_at"]} for r in rows])

    def delete_passkey(self,key_id):
        user=self.require_user()
        if not user:return
        with connect() as db:changed=db.execute("DELETE FROM passkeys WHERE id=? AND user_id=?",(key_id,user["id"])).rowcount
        if changed:self.audit("passkey.removed","passkey",key_id)
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def list_audit_events(self):
        user=self.require_user()
        if not user:return
        with connect() as db:rows=db.execute("SELECT id,action,target_type,target_id,metadata_json,ip_address,previous_hash,event_hash,created_at FROM audit_events WHERE user_id=? ORDER BY created_at DESC LIMIT 200",(user["id"],)).fetchall()
        result=[]
        for r in rows:
            try:meta=json.loads(r["metadata_json"] or "{}")
            except Exception:meta={}
            result.append({"id":r["id"],"action":r["action"],"targetType":r["target_type"],"targetId":r["target_id"],"metadata":meta,"ipAddress":r["ip_address"],"createdAt":r["created_at"],"hash":r["event_hash"]})
        self.json(200,result)

    def update_privacy_preferences(self):
        user=self.require_user()
        if not user:return
        data=self.body(30_000);privacy={"analyticsConsent":bool(data.get("analyticsConsent",False)),"externalMediaConsent":bool(data.get("externalMediaConsent",False)),"guestDataRetentionDays":max(1,min(3650,int(data.get("guestDataRetentionDays",365))))}
        with connect() as db:db.execute("UPDATE users SET privacy_json=? WHERE id=?",(json.dumps(privacy),user["id"]))
        self.audit("privacy.preferences_updated","user",user["id"],privacy);self.json(200,{"privacy":privacy})

    def schedule_account_deletion(self):
        user=self.require_user()
        if not user:return
        data=self.body(30_000);password=str(data.get("password","") or "")
        with connect() as db:
            row=db.execute("SELECT password_hash,salt,password_algo FROM users WHERE id=?",(user["id"],)).fetchone();valid,_=account_verify_password(password,row["password_hash"],row["salt"],row["password_algo"] if row else "") if row else (False,False)
            if not valid:return self.json(401,{"error":"Password confirmation is required"})
            now=int(time.time()*1000);purge=now+ACCOUNT_TRASH_DAYS*24*60*60*1000;db.execute("UPDATE users SET deletion_scheduled_at=? WHERE id=?",(purge,user["id"]))
        self.audit("account.deletion_scheduled","user",user["id"],{"purgeAt":purge});self.json(200,{"scheduled":True,"purgeAt":purge})

    def cancel_account_deletion(self):
        user=self.require_user()
        if not user:return
        with connect() as db:db.execute("UPDATE users SET deletion_scheduled_at=NULL WHERE id=?",(user["id"],))
        self.audit("account.deletion_cancelled","user",user["id"]);self.json(200,{"scheduled":False})

    def export_account_archive(self):
        user=self.require_user()
        if not user:return
        raw,_=build_studio_archive(user["id"],include_media=True)
        self.send_response(200);self.send_header("Content-Type","application/zip");self.send_header("Content-Disposition",f'attachment; filename="einvite-account-export-{int(time.time())}.zip"');self.send_header("Cache-Control","private,no-store");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)

    def list_invitations(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT i.id,i.slug,i.updated_at,i.archived,i.views,i.access_mode,i.is_published,CASE WHEN i.is_published=1 THEN 'Published' ELSE 'Draft' END status,(SELECT COUNT(*) FROM rsvps r WHERE r.invitation_id=i.id) rsvps,i.draft_json,i.owner_id,COALESCE((SELECT role FROM invitation_collaborators c WHERE c.invitation_id=i.id AND c.user_id=?),'owner') collaboration_role FROM invitations i WHERE i.deleted_at IS NULL AND (i.owner_id=? OR EXISTS(SELECT 1 FROM invitation_collaborators c WHERE c.invitation_id=i.id AND c.user_id=?)) ORDER BY i.archived,i.updated_at DESC",(user["id"],user["id"],user["id"])).fetchall()
        result=[]
        for row in rows:
            draft=json.loads(row["draft_json"])
            # A lightweight preview payload lets the dashboard render the actual invitation
            # design without downloading a second document for every project card.
            preview={
                "eventType":draft.get("eventType","Invitation"),
                "theme":draft.get("theme","rose"),
                "accent":draft.get("accent","#9d4555"),
                "palette":draft.get("palette",{}),
                "fields":draft.get("fields",{}),
                "objects":draft.get("objects",{}),
                "designPages":[p for p in draft.get("designPages",[]) if p.get("enabled",True)][:1],
                "masterPageStyle":draft.get("masterPageStyle",{}),
            }
            result.append({"id":row["id"],"slug":row["slug"],"title":draft.get("fields",{}).get("names","Untitled invitation"),"type":draft.get("eventType","Invitation"),"status":"Archived" if row["archived"] else row["status"],"archived":bool(row["archived"]),"views":row["views"],"rsvps":row["rsvps"],"rsvpEnabled":draft.get("settings",{}).get("rsvpEnabled") is not False,"accessMode":row["access_mode"] or "unlisted","updatedAt":row["updated_at"],"shared":row["owner_id"]!=user["id"],"collaborationRole":row["collaboration_role"],"preview":preview})
        self.json(200,result)
    def create_invitation(self):
        user=self.require_user()
        if not user:return
        if not self.require_plan_capacity(user,"invitations"):return
        data = self.body(); document=validate_document(data.get("document",{})); invite_id = str(uuid.uuid4()); slug = clean_slug(data.get("slug", "our-invitation")); now = int(time.time()*1000)
        workspace=get_platform_v32_service().workspace_for_user(user["id"])
        with connect() as db:
            base=slug; n=2
            while db.execute("SELECT 1 FROM invitations WHERE slug=?",(slug,)).fetchone(): slug=f"{base}-{n}"; n+=1
            db.execute("INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id,workspace_id,document_epoch,document_version) VALUES(?,?,?,?,?,?,1,0)",(invite_id,slug,json.dumps(document),now,user["id"],workspace["id"]))
        self.json(201,{"id":invite_id,"slug":slug,"updatedAt":now})
    def get_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT id,slug,draft_json,updated_at,archived,access_mode,is_published,owner_id,last_client_id,last_mutation_id,custom_domain,publish_at,unpublish_at,expires_at,gallery_access_password_hash FROM invitations WHERE id=?",(invite_id,)).fetchone()
            role=self.invitation_role(db,invite_id,user["id"])
        if not row:return self.json(404,{"error":"Invitation not found"})
        self.json(200,{"id":row["id"],"slug":row["slug"],"document":json.loads(row["draft_json"]),"updatedAt":row["updated_at"],"archived":bool(row["archived"]),"accessMode":row["access_mode"] or "unlisted","published":bool(row["is_published"]),"collaborationRole":role,"owner":row["owner_id"]==user["id"],"lastClientId":row["last_client_id"],"lastMutationId":row["last_mutation_id"],"customDomain":row["custom_domain"] or "","publishAt":row["publish_at"],"unpublishAt":row["unpublish_at"],"expiresAt":row["expires_at"],"galleryProtected":bool(row["gallery_access_password_hash"])})
    def archive_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(10_000); archived=1 if data.get("archived",True) else 0;now=int(time.time()*1000);client_id,mutation_id=self.mutation_identity()
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            changed=db.execute("UPDATE invitations SET archived=?,updated_at=?,last_client_id=?,last_mutation_id=? WHERE id=?",(archived,now,client_id or None,mutation_id or None,invite_id)).rowcount
        self.json(200 if changed else 404,{"archived":bool(archived),"updatedAt":now,"clientId":client_id or None,"mutationId":mutation_id or None})
    def update_slug(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);slug=clean_slug(data.get("slug",""))
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            if db.execute("SELECT 1 FROM invitations WHERE slug=? AND id<>?",(slug,invite_id)).fetchone():return self.json(409,{"error":"That public link is already in use"})
            now=int(time.time()*1000);client_id,mutation_id=self.mutation_identity();db.execute("UPDATE invitations SET slug=?,updated_at=?,last_client_id=?,last_mutation_id=? WHERE id=? AND owner_id=?",(slug,now,client_id or None,mutation_id or None,invite_id,user["id"]))
        self.json(200,{"slug":slug,"url":f"/i/{slug}","updatedAt":now,"clientId":client_id or None,"mutationId":mutation_id or None})

    def update_access(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);mode=str(data.get("mode","unlisted"))
        if mode not in {"unlisted","password"}:raise ValueError("Invalid invitation access mode")
        password=str(data.get("password", ""));salt=None;hashed=None
        with connect() as db:
            row=db.execute("SELECT access_password_hash,access_password_salt FROM invitations WHERE id=? AND owner_id=?",(invite_id,user["id"])).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            if mode=="password":
                if password:
                    if len(password)<8 or len(password)>120:raise ValueError("Invitation password must be 8 to 120 characters")
                    salt=secrets.token_hex(16);hashed=password_hash(password,salt)
                elif row["access_password_hash"]:
                    hashed=row["access_password_hash"];salt=row["access_password_salt"]
                else:raise ValueError("Set an invitation password before enabling password protection")
            now=int(time.time()*1000);client_id,mutation_id=self.mutation_identity();db.execute("UPDATE invitations SET access_mode=?,access_password_hash=?,access_password_salt=?,updated_at=?,last_client_id=?,last_mutation_id=? WHERE id=? AND owner_id=?",(mode,hashed,salt,now,client_id or None,mutation_id or None,invite_id,user["id"]))
            db.execute("DELETE FROM access_tokens WHERE invitation_id=?",(invite_id,))
        self.json(200,{"accessMode":mode,"updatedAt":now,"clientId":client_id or None,"mutationId":mutation_id or None})

    def get_analytics(self,invite_id):
        user=self.require_user()
        if not user:return
        now=int(time.time()*1000);start=now-30*24*60*60*1000
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            invite=db.execute("SELECT views,draft_json FROM invitations WHERE id=?",(invite_id,)).fetchone()
            rows=db.execute("SELECT viewed_at FROM view_events WHERE invitation_id=? AND viewed_at>=? ORDER BY viewed_at",(invite_id,start)).fetchall()
            rsvps=db.execute("SELECT status,guest_count,created_at FROM rsvps WHERE invitation_id=?",(invite_id,)).fetchall()
            guests=db.execute("SELECT checked_in FROM guests WHERE invitation_id=?",(invite_id,)).fetchall()
        by_day={}
        for row in rows:
            day=time.strftime('%Y-%m-%d',time.localtime(row["viewed_at"]/1000));by_day[day]=by_day.get(day,0)+1
        statuses={}
        for row in rsvps:statuses[row["status"]]=statuses.get(row["status"],0)+1
        try:rsvp_enabled=json.loads(invite["draft_json"] or "{}").get("settings",{}).get("rsvpEnabled") is not False
        except Exception:rsvp_enabled=True
        self.json(200,{"totalViews":int(invite["views"] or 0),"views30Days":len(rows),"viewsByDay":by_day,"rsvpEnabled":rsvp_enabled,"rsvpTotal":len(rsvps),"rsvpGuests":sum(int(r["guest_count"] or 0) for r in rsvps),"rsvpStatuses":statuses,"guestListTotal":len(guests),"checkedIn":sum(1 for g in guests if g["checked_in"])})

    def list_trash(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT id,slug,draft_json,deleted_at,purge_at FROM invitations WHERE owner_id=? AND deleted_at IS NOT NULL ORDER BY deleted_at DESC",(user["id"],)).fetchall()
        result=[]
        for row in rows:
            try:d=json.loads(row["draft_json"] or "{}")
            except Exception:d={}
            result.append({"id":row["id"],"slug":row["slug"],"title":d.get("fields",{}).get("names","Untitled invitation"),"deletedAt":row["deleted_at"],"purgeAt":row["purge_at"]})
        self.json(200,result)

    def trash_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        now=int(time.time()*1000);purge=now+ACCOUNT_TRASH_DAYS*24*60*60*1000
        with connect() as db:
            changed=db.execute("UPDATE invitations SET deleted_at=?,purge_at=?,is_published=0,updated_at=? WHERE id=? AND owner_id=? AND deleted_at IS NULL",(now,purge,now,invite_id,user["id"])).rowcount
        if not changed:return self.json(404,{"error":"Invitation not found"})
        self.audit("invitation.trashed","invitation",invite_id,{"purgeAt":purge})
        self.json(200,{"trashed":True,"purgeAt":purge})

    def restore_trashed_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        now=int(time.time()*1000)
        with connect() as db:
            changed=db.execute("UPDATE invitations SET deleted_at=NULL,purge_at=NULL,updated_at=? WHERE id=? AND owner_id=? AND deleted_at IS NOT NULL",(now,invite_id,user["id"])).rowcount
        if not changed:return self.json(404,{"error":"Trashed invitation not found"})
        self.audit("invitation.restored","invitation",invite_id)
        self.json(200,{"restored":True,"updatedAt":now})

    def delete_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        purge=[]
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            asset_rows=db.execute("SELECT object_id,path,sha256 FROM assets WHERE invitation_id=?",(invite_id,)).fetchall()
            db.execute("DELETE FROM rsvps WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM guest_messages WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM view_events WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM access_tokens WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM gallery_access_tokens WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM publications WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM assets WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM guests WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_collaborators WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_comments WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM approval_requests WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_review_policies WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM review_notifications WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM review_tasks WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitation_studio_release_pins WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM upload_sessions WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM material_import_jobs WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM material_folders WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitations WHERE id=?",(invite_id,))
            purge=release_stored_object_references(db,[row["object_id"] for row in asset_rows])
            # Legacy fallback for an unmigrated row. The physical object is deleted
            # only when no remaining asset row references its path.
            for row in asset_rows:
                if row["object_id"]:continue
                if not db.execute("SELECT 1 FROM assets WHERE path=? LIMIT 1",(row["path"],)).fetchone():purge.append((row["path"],row["sha256"]))
        queue_physical_deletions(purge)
        self.audit("invitation.deleted","invitation",invite_id,{"permanent":True})
        self.json(200,{"deleted":True})
    def save_draft(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(); document=validate_document(data.get("document",{})); client_id,mutation_id=self.mutation_identity();expected=data.get("expectedRevision")
        if expected is not None:
            try:expected=int(expected)
            except (TypeError,ValueError):raise ValueError("Invalid expected revision")
            if expected<0:raise ValueError("Invalid expected revision")
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            row=db.execute("SELECT updated_at,last_client_id,last_mutation_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            current=int(row["updated_at"] or 0)
            if expected is not None and expected!=current:
                return self.json(409,{"error":"This invitation changed in another session. Reload the latest version before saving again.","code":"revision_conflict","updatedAt":current,"clientId":row["last_client_id"],"mutationId":row["last_mutation_id"]})
            now=max(int(time.time()*1000),current+1)
            if expected is None:
                changed=db.execute("UPDATE invitations SET draft_json=?,updated_at=?,last_client_id=?,last_mutation_id=?,document_version=COALESCE(document_version,0)+1 WHERE id=?",(json.dumps(document),now,client_id or None,mutation_id or None,invite_id)).rowcount
            else:
                changed=db.execute("UPDATE invitations SET draft_json=?,updated_at=?,last_client_id=?,last_mutation_id=?,document_version=COALESCE(document_version,0)+1 WHERE id=? AND updated_at=?",(json.dumps(document),now,client_id or None,mutation_id or None,invite_id,current)).rowcount
                if not changed:
                    latest=db.execute("SELECT updated_at,last_client_id,last_mutation_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
                    return self.json(409,{"error":"This invitation changed in another session. Reload the latest version before saving again.","code":"revision_conflict","updatedAt":int(latest["updated_at"] or current) if latest else current,"clientId":latest["last_client_id"] if latest else None,"mutationId":latest["last_mutation_id"] if latest else None})
        self.json(200 if changed else 404,{"saved":bool(changed),"updatedAt":now,"clientId":client_id or None,"mutationId":mutation_id or None})
    def publish(self, invite_id):
        user=self.require_user()
        if not user:return
        if REQUIRE_VERIFIED_EMAIL and not self.require_verified_for_sensitive_action(user,"publishing invitations"):return
        data=self.body();pub_id=str(uuid.uuid4());client_id,mutation_id=self.mutation_identity();expected=data.get("expectedRevision")
        if expected is not None:
            try:expected=int(expected)
            except (TypeError,ValueError):raise ValueError("Invalid expected revision")
            if expected<0:raise ValueError("Invalid expected revision")
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Publishing permission required"})
            row=db.execute("SELECT slug,draft_json,access_mode,owner_id,updated_at,last_client_id,last_mutation_id,document_version FROM invitations WHERE id=?",(invite_id,)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            current=int(row["updated_at"] or 0)
            if expected is not None and expected!=current:return self.json(409,{"error":"This invitation changed in another session. Reload the latest version before publishing again.","code":"revision_conflict","updatedAt":current,"clientId":row["last_client_id"],"mutationId":row["last_mutation_id"]})
            readiness=self._review_readiness(db,invite_id)
            if readiness and not readiness["ready"]:return self.json(409,{"error":"Publishing is blocked by the invitation review policy.","code":"review_gate_blocked","readiness":readiness})
            document=validate_document(data.get("document") or json.loads(row["draft_json"]));studio_readiness=studio_publish_readiness(db,row["owner_id"],document,invite_id)
            if studio_readiness and not studio_readiness["ready"]:return self.json(409,{"error":"Publishing is blocked by the studio design policy.","code":"studio_governance_blocked","readiness":studio_readiness})
            platform_readiness=get_platform_v32_service().publication_readiness(invite_id,user["id"],document)
            if not platform_readiness["ready"]:return self.json(409,{"error":"Publishing is blocked because an advanced asset is missing a safe public rendition.","code":"platform_publication_blocked","readiness":platform_readiness})
            now=max(int(time.time()*1000),current+1);new_document_version=int(row["document_version"] or 0)+1
            changed=db.execute("UPDATE invitations SET draft_json=?,is_published=1,updated_at=?,last_client_id=?,last_mutation_id=?,document_version=? WHERE id=? AND updated_at=?",(json.dumps(document),now,client_id or None,mutation_id or None,new_document_version,invite_id,current)).rowcount
            if not changed:
                latest=db.execute("SELECT updated_at,last_client_id,last_mutation_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
                return self.json(409,{"error":"This invitation changed in another session. Reload the latest version before publishing again.","code":"revision_conflict","updatedAt":int(latest["updated_at"] or current) if latest else current,"clientId":latest["last_client_id"] if latest else None,"mutationId":latest["last_mutation_id"] if latest else None})
            db.execute("INSERT INTO publications(id,invitation_id,version,document_json,published_at,workspace_id,snapshot_fingerprint,document_epoch,document_version) VALUES(?,?,?,?,?,?,?,?,?)",(pub_id,invite_id,now,json.dumps(document),now,platform_readiness["workspaceId"],platform_readiness["fingerprint"],platform_readiness["documentEpoch"],new_document_version));invalidate_social_cache(invite_id)
        schedule_social_warm(invite_id,row["access_mode"],now,document);self.audit("invitation.published","invitation",invite_id,{"publicationId":pub_id,"version":now})
        self.json(201,{"publicationId":pub_id,"version":now,"updatedAt":now,"documentVersion":new_document_version,"clientId":client_id or None,"mutationId":mutation_id or None,"slug":row["slug"],"url":f"/i/{row['slug']}"})
    def unpublish(self, invite_id):
        user=self.require_user()
        if not user:return
        now=int(time.time()*1000);client_id,mutation_id=self.mutation_identity()
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Publishing permission required"})
            changed=db.execute("UPDATE invitations SET is_published=0,updated_at=?,last_client_id=?,last_mutation_id=? WHERE id=?",(now,client_id or None,mutation_id or None,invite_id)).rowcount
        if changed:self.audit("invitation.unpublished","invitation",invite_id)
        self.json(200 if changed else 404,{"published":False,"savedVersionsPreserved":True,"updatedAt":now,"clientId":client_id or None,"mutationId":mutation_id or None})

    def update_presence(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);client_id=str(data.get("clientId","")).strip()[:120] or secrets.token_urlsafe(12);now=int(time.time()*1000);payload={"userId":user["id"],"email":user["email"],"clientId":client_id,"mode":str(data.get("mode","editing"))[:40],"selectedObjectId":str(data.get("selectedObjectId","")).strip()[:120],"updatedAt":now}
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        client=redis_client()
        if client:
            try:client.setex(f"einvite:presence:{invite_id}:{user['id']}:{client_id}",45,json.dumps(payload,ensure_ascii=False))
            except Exception:client=None
        if not client:
            with PRESENCE_LOCK:
                PRESENCE_STATE[(invite_id,user["id"],client_id)]=payload
                cutoff=now-60_000
                for key,value in list(PRESENCE_STATE.items()):
                    if value.get("updatedAt",0)<cutoff:PRESENCE_STATE.pop(key,None)
        self.json(200,{"self":payload,"presence":current_presence(invite_id)})

    def list_presence(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        self.json(200,current_presence(invite_id))

    def invitation_events(self, invite_id):
        """Short-lived SSE stream for collaboration change notifications.

        This provides near-real-time remote-change awareness without pretending to be a
        conflict-free collaborative document engine. EventSource reconnects automatically;
        the editor still asks before replacing unsaved local work.
        """
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        self.send_response(200)
        self.send_header("Content-Type","text/event-stream; charset=utf-8")
        self.send_header("Cache-Control","no-cache, no-transform")
        self.send_header("Connection","keep-alive")
        self.end_headers()
        last=None
        try:
            for tick in range(30):
                with connect() as db:row=db.execute("SELECT updated_at,last_client_id,last_mutation_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
                if not row:break
                updated=int(row["updated_at"] or 0)
                if updated!=last:
                    payload=json.dumps({"updatedAt":updated,"clientId":row["last_client_id"],"mutationId":row["last_mutation_id"]},separators=(",",":"))
                    self.wfile.write(f"event: invitation-update\ndata: {payload}\n\n".encode());self.wfile.flush();last=updated
                elif tick%5==0:
                    self.wfile.write(b": keep-alive\n\n");self.wfile.flush()
                time.sleep(2)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

    def get_collaborators(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Management permission required"})
            rows=db.execute("SELECT c.user_id,c.role,c.created_at,u.email FROM invitation_collaborators c JOIN users u ON u.id=c.user_id WHERE c.invitation_id=? ORDER BY c.created_at",(invite_id,)).fetchall()
        self.json(200,[{"userId":r["user_id"],"email":r["email"],"role":r["role"],"createdAt":r["created_at"]} for r in rows])
    def add_collaborator(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);email=str(data.get("email","")).strip().lower();role=str(data.get("role","viewer")).lower()
        if role not in {"viewer","content","designer","manager"}:raise ValueError("Invalid collaborator role")
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Management permission required"})
            target=db.execute("SELECT id,email FROM users WHERE email=?",(email,)).fetchone()
            if not target:return self.json(404,{"error":"That email does not have an account yet"})
            owner=db.execute("SELECT owner_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
            if owner and owner["owner_id"]==target["id"]:return self.json(409,{"error":"The invitation owner already has full access"})
            db.execute("INSERT INTO invitation_collaborators(invitation_id,user_id,role,created_at) VALUES(?,?,?,?) ON CONFLICT(invitation_id,user_id) DO UPDATE SET role=excluded.role",(invite_id,target["id"],role,int(time.time()*1000)))
        self.audit("collaborator.updated","invitation",invite_id,{"collaboratorUserId":target["id"],"role":role})
        self.json(200,{"userId":target["id"],"email":target["email"],"role":role})
    def delete_collaborator(self, invite_id, collaborator_user_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Management permission required"})
            changed=db.execute("DELETE FROM invitation_collaborators WHERE invitation_id=? AND user_id=?",(invite_id,collaborator_user_id)).rowcount
        if changed:self.audit("collaborator.removed","invitation",invite_id,{"collaboratorUserId":collaborator_user_id})
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def access_token_valid(self, db, invitation_id, token):
        if not token:return False
        token_hash=hashlib.sha256(str(token).encode()).hexdigest();now=int(time.time()*1000)
        return db.execute("SELECT 1 FROM access_tokens WHERE token_hash=? AND invitation_id=? AND expires_at>?",(token_hash,invitation_id,now)).fetchone() is not None

    def lookup_guest_by_token(self, db, invitation_id, token):
        if not token:return None
        now=int(time.time()*1000);token_hash=guest_token_hash(token)
        return db.execute("SELECT id,name,group_name,household_id,table_name,seat_label FROM guests WHERE invitation_id=? AND token_hash=? AND token_revoked_at IS NULL AND (token_expires_at IS NULL OR token_expires_at>?)",(invitation_id,token_hash,now)).fetchone()

    def current_guest_token(self, row):
        if not row or not row.get("token_salt") if isinstance(row,dict) else not row["token_salt"]:return None
        salt=row.get("token_salt") if isinstance(row,dict) else row["token_salt"]
        version=row.get("token_version") if isinstance(row,dict) else row["token_version"]
        return guest_token_value(row.get("id") if isinstance(row,dict) else row["id"],salt,version or 1)

    def get_public(self, slug, guest_token=None, access_token=None, gallery_access_token=None):
        with connect() as db:
            row=db.execute("SELECT i.id,i.access_mode,i.gallery_access_password_hash,i.gallery_access_password_salt,i.owner_id,p.id publication_id,p.version,p.document_json,u.studio_name,u.white_label_json FROM invitations i JOIN publications p ON p.invitation_id=i.id LEFT JOIN users u ON u.id=i.owner_id WHERE i.slug=? AND i.archived=0 AND i.deleted_at IS NULL AND i.is_published=1 AND (i.expires_at IS NULL OR i.expires_at>?) ORDER BY p.published_at DESC LIMIT 1",(slug,int(time.time()*1000))).fetchone()
            if not row:return self.json(404,{"error":"Published invitation not found"})
            if row["access_mode"]=="password" and not self.access_token_valid(db,row["id"],access_token):return self.json(403,{"error":"Password required","protected":True})
            try: public_document=json.loads(row["document_json"] or "{}")
            except Exception: public_document={}
            privacy=public_document.get("privacy") if isinstance(public_document.get("privacy"),dict) else {}
            analytics_consent_required=bool(privacy.get("analyticsConsentRequired",False))
            external_media_consent_required=bool(privacy.get("externalMediaConsentRequired",False))
            gallery_protected=bool(row["gallery_access_password_hash"] and (public_document.get("galleryProtection") or {}).get("enabled"))
            gallery_authorized=not gallery_protected or gallery_access_token_valid(db,row["id"],gallery_access_token)
            if not analytics_consent_required:
                db.execute("UPDATE invitations SET views=views+1 WHERE id=?",(row["id"],));db.execute("INSERT INTO view_events VALUES(?,?,?,?)",(str(uuid.uuid4()),row["id"],row["publication_id"],int(time.time()*1000)))
        guest=None
        if guest_token:
            with connect() as db:
                guest=self.lookup_guest_by_token(db,row["id"],guest_token)
                if guest:db.execute("UPDATE guests SET opened_at=COALESCE(opened_at,?),delivery_status=CASE WHEN delivery_status='sent' THEN 'opened' ELSE delivery_status END WHERE id=?",(int(time.time()*1000),guest["id"]))
        document=apply_gallery_access(public_document,row["id"],gallery_authorized)
        if row["access_mode"]=="password":document=rewrite_document_media_urls(document,row["id"])
        try:studio_white=json.loads(row["white_label_json"] or "{}")
        except Exception:studio_white={}
        studio_brand={"name":row["studio_name"] or "","logo":studio_white.get("logo","") or "","primaryColor":studio_white.get("primaryColor","") or "","accentColor":studio_white.get("accentColor","") or "","website":studio_white.get("website","") or "","hidePlatformBrand":bool(studio_white.get("hidePlatformBrand",False))}
        self.json(200,{"invitationId":row["id"],"publicationId":row["publication_id"],"version":row["version"],"document":document,"guest":dict(guest) if guest else None,"analyticsConsentRequired":analytics_consent_required,"externalMediaConsentRequired":external_media_consent_required,"galleryProtected":gallery_protected,"galleryAuthorized":gallery_authorized,"studioBrand":studio_brand})

    def update_gallery_access(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(30_000);enabled=bool(data.get("enabled",False));password=str(data.get("password","") or "")
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Management permission required"})
            if enabled and password:
                if len(password)<8:return self.json(400,{"error":"Gallery password must contain at least 8 characters"})
                salt=secrets.token_hex(16);digest=password_hash(password,salt);db.execute("UPDATE invitations SET gallery_access_password_hash=?,gallery_access_password_salt=?,updated_at=? WHERE id=?",(digest,salt,int(time.time()*1000),invite_id))
            elif not enabled:
                db.execute("UPDATE invitations SET gallery_access_password_hash=NULL,gallery_access_password_salt=NULL,updated_at=? WHERE id=?",(int(time.time()*1000),invite_id));db.execute("DELETE FROM gallery_access_tokens WHERE invitation_id=?",(invite_id,))
            else:
                row=db.execute("SELECT gallery_access_password_hash FROM invitations WHERE id=?",(invite_id,)).fetchone()
                if not row or not row["gallery_access_password_hash"]:return self.json(400,{"error":"Set a gallery password before enabling protection"})
        self.audit("gallery.access_updated","invitation",invite_id,{"enabled":enabled,"passwordChanged":bool(password)})
        self.json(200,{"enabled":enabled,"passwordSet":enabled})

    def unlock_public_gallery(self,slug):
        if not self.rate_limit(f"gallery-unlock:{self.client_ip()}:{slug}",12,600):return
        data=self.body(30_000);password=str(data.get("password","") or "");now=int(time.time()*1000)
        if not self.bot_protection_ok("gallery-unlock",data.get("botToken","")):return self.json(403,{"error":"Gallery unlock verification failed"})
        with connect() as db:
            row=db.execute("SELECT id,gallery_access_password_hash,gallery_access_password_salt FROM invitations WHERE slug=? AND archived=0 AND deleted_at IS NULL AND is_published=1 AND (expires_at IS NULL OR expires_at>?)",(slug,now)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            if not row["gallery_access_password_hash"]:return self.json(200,{"galleryAccessToken":None})
            if not row["gallery_access_password_salt"] or not hmac.compare_digest(row["gallery_access_password_hash"],password_hash(password,row["gallery_access_password_salt"])):return self.json(401,{"error":"Incorrect gallery password"})
            token=secrets.token_urlsafe(24);expires=now+12*60*60*1000;db.execute("INSERT INTO gallery_access_tokens(token_hash,invitation_id,expires_at,created_at) VALUES(?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),row["id"],expires,now))
        self.json(200,{"galleryAccessToken":token,"expiresAt":expires})

    def record_public_view(self, slug):
        if not self.rate_limit(f"public-view:{self.client_address[0]}:{slug}",4,3600):return
        now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT i.id,p.id publication_id FROM invitations i JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? AND i.archived=0 AND i.deleted_at IS NULL AND i.is_published=1 AND (i.expires_at IS NULL OR i.expires_at>?) ORDER BY p.published_at DESC LIMIT 1",(slug,now)).fetchone()
            if not row:return self.json(404,{"error":"Published invitation not found"})
            db.execute("UPDATE invitations SET views=views+1 WHERE id=?",(row["id"],));db.execute("INSERT INTO view_events VALUES(?,?,?,?)",(str(uuid.uuid4()),row["id"],row["publication_id"],now))
        self.json(200,{"recorded":True})

    def unlock_public(self, slug):
        if not self.rate_limit(f"unlock:{self.client_address[0]}:{slug}",12,600):return
        data=self.body(50_000);password=str(data.get("password",""));now=int(time.time()*1000)
        if not self.bot_protection_ok("invitation-unlock",data.get("botToken","")):return self.json(403,{"error":"Unlock verification failed"})
        with connect() as db:
            row=db.execute("SELECT id,access_mode,access_password_hash,access_password_salt FROM invitations WHERE slug=? AND archived=0 AND deleted_at IS NULL",(slug,)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            if row["access_mode"]!="password":return self.json(200,{"accessToken":None})
            if not row["access_password_hash"] or not row["access_password_salt"] or not hmac.compare_digest(row["access_password_hash"],password_hash(password,row["access_password_salt"])):return self.json(401,{"error":"Incorrect invitation password"})
            token=secrets.token_urlsafe(24);expires=now+24*60*60*1000;db.execute("INSERT INTO access_tokens VALUES(?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),row["id"],expires,now))
        self.json(200,{"accessToken":token,"expiresAt":expires})

    def update_guest_details(self,invite_id,guest_id):
        user=self.require_user()
        if not user:return
        data=self.body(100_000);tags=data.get("tags",[]);tags=tags if isinstance(tags,list) else []
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            changed=db.execute("UPDATE guests SET name=?,phone=?,email=?,group_name=?,household_id=?,tags_json=?,table_name=?,seat_label=? WHERE id=? AND invitation_id=?",(str(data.get("name","")).strip()[:120],str(data.get("phone","")).strip()[:40],str(data.get("email","")).strip()[:254],str(data.get("groupName","")).strip()[:80],str(data.get("householdId","")).strip()[:80],json.dumps([str(x)[:50] for x in tags[:20]],ensure_ascii=False),str(data.get("tableName","")).strip()[:80],str(data.get("seatLabel","")).strip()[:40],guest_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"updated":bool(changed)})

    def update_invitation_operations(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(100_000);now=int(time.time()*1000)
        def stamp(value):
            if value in (None,""):return None
            try:return int(value)
            except Exception:raise ValueError("Invalid schedule timestamp")
        publish_at,unpublish_at,expires_at=stamp(data.get("publishAt")),stamp(data.get("unpublishAt")),stamp(data.get("expiresAt"));domain=valid_custom_domain(data.get("customDomain",""))
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            if domain and db.execute("SELECT 1 FROM invitations WHERE custom_domain=? AND id<>?",(domain,invite_id)).fetchone():return self.json(409,{"error":"That custom domain is already assigned"})
            if publish_at:
                row=db.execute("SELECT draft_json FROM invitations WHERE id=?",(invite_id,)).fetchone();doc=validate_document(json.loads(row["draft_json"]));db.execute("INSERT INTO publications(id,invitation_id,version,document_json,published_at,workspace_id,snapshot_fingerprint,document_epoch,document_version) SELECT ?,?,?,?, ?,workspace_id,?,COALESCE(document_epoch,1),COALESCE(document_version,0) FROM invitations WHERE id=?",(str(uuid.uuid4()),invite_id,publish_at,json.dumps(doc),publish_at,hashlib.sha256(json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest(),invite_id))
            db.execute("UPDATE invitations SET custom_domain=?,publish_at=?,unpublish_at=?,expires_at=?,updated_at=? WHERE id=?",(domain or None,publish_at,unpublish_at,expires_at,now,invite_id))
        self.audit("invitation.operations_updated","invitation",invite_id,{"customDomain":domain,"publishAt":publish_at,"unpublishAt":unpublish_at,"expiresAt":expires_at})
        self.json(200,{"customDomain":domain,"publishAt":publish_at,"unpublishAt":unpublish_at,"expiresAt":expires_at})

    def list_campaigns(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT * FROM message_campaigns WHERE invitation_id=? ORDER BY created_at DESC",(invite_id,)).fetchall()
        self.json(200,[{**dict(r),"segment":json.loads(r["segment_json"] or "{}") } for r in rows])

    def create_campaign(self,invite_id):
        user=self.require_user()
        if not user:return
        if REQUIRE_VERIFIED_EMAIL and not self.require_verified_for_sensitive_action(user,"creating delivery campaigns"):return
        data=self.body(100_000);channel=str(data.get("channel","email")).lower()
        if channel not in {"email","sms","whatsapp","telegram"}:raise ValueError("Unsupported campaign channel")
        segment=data.get("segment",{}) if isinstance(data.get("segment",{}),dict) else {};now=int(time.time()*1000);cid=str(uuid.uuid4())
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            scheduled_at=data.get("scheduledAt");
            try:scheduled_at=int(scheduled_at) if scheduled_at not in (None,'') else None
            except (TypeError,ValueError):raise ValueError("Invalid campaign schedule")
            state='scheduled' if scheduled_at and scheduled_at>now else 'draft';db.execute("INSERT INTO message_campaigns(id,invitation_id,owner_id,name,channel,message,segment_json,state,scheduled_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(cid,invite_id,user["id"],str(data.get("name","Invitation delivery"))[:120],channel,str(data.get("message","You are invited"))[:5000],json.dumps(segment),state,scheduled_at,now,now))
        self.audit("campaign.created","campaign",cid,{"invitationId":invite_id,"channel":channel,"state":state});self.json(201,{"id":cid,"state":state,"scheduledAt":scheduled_at})

    def dispatch_campaign(self,invite_id,campaign_id):
        user=self.require_user()
        if not user:return
        if REQUIRE_VERIFIED_EMAIL and not self.require_verified_for_sensitive_action(user,"sending invitation messages"):return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            campaign=db.execute("SELECT * FROM message_campaigns WHERE id=? AND invitation_id=?",(campaign_id,invite_id)).fetchone()
            if not campaign:return self.json(404,{"error":"Campaign not found"})
            segment=json.loads(campaign["segment_json"] or "{}");rows=db.execute("SELECT * FROM guests WHERE invitation_id=?",(invite_id,)).fetchall()
        guests=[]
        for r in rows:
            tags=json.loads(r["tags_json"] or "[]")
            if segment.get("group") and r["group_name"]!=segment["group"]:continue
            if segment.get("tag") and segment["tag"] not in tags:continue
            guests.append(r)
        sent=preview=failed=0
        with connect() as db:
            for guest in guests:
                recipient=guest["email"] if campaign["channel"]=='email' else guest["phone"]
                result=send_message_provider(campaign["channel"],recipient,campaign["message"],{"guestName":guest["name"],"invitationId":invite_id})
                status=result.get("status","failed");sent+=status=='sent';preview+=status in {'preview','queued'};failed+=status in {'failed','skipped'};did=str(uuid.uuid4());now=int(time.time()*1000)
                db.execute("INSERT INTO message_deliveries(id,campaign_id,guest_id,channel,status,provider_id,error,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(did,campaign_id,guest["id"],campaign["channel"],status,result.get("providerId",''),result.get("error",''),now,now))
                if status=='sent':db.execute("UPDATE guests SET delivery_status='sent' WHERE id=?",(guest["id"],))
            db.execute("UPDATE message_campaigns SET state=?,updated_at=? WHERE id=?",('sent' if failed==0 else 'partial',int(time.time()*1000),campaign_id))
        self.audit("campaign.dispatched","campaign",campaign_id,{"sent":sent,"preview":preview,"failed":failed});self.json(200,{"sent":sent,"preview":preview,"failed":failed,"providerConfigured":bool(MESSAGING_WEBHOOK_ENDPOINT or campaign["channel"]=='email')})

    def _review_document_state(self,db,invite_id):
        row=db.execute("SELECT updated_at,draft_json FROM invitations WHERE id=?",(invite_id,)).fetchone()
        if not row:return None
        raw=str(row["draft_json"] or "{}")
        return {"revision":int(row["updated_at"] or 0),"fingerprint":hashlib.sha256(raw.encode()).hexdigest()[:24],"raw":raw}

    def _review_policy(self,db,invite_id):
        row=db.execute("SELECT * FROM invitation_review_policies WHERE invitation_id=?",(invite_id,)).fetchone()
        if not row:return {"approvalGate":False,"unresolvedCommentsGate":False,"minApprovals":1,"updatedAt":0,"updatedBy":""}
        return {"approvalGate":bool(row["approval_gate"]),"unresolvedCommentsGate":bool(row["unresolved_comments_gate"]),"minApprovals":max(1,min(5,int(row["min_approvals"] or 1))),"updatedAt":int(row["updated_at"] or 0),"updatedBy":str(row["updated_by"] or "")}

    def _review_readiness(self,db,invite_id):
        state=self._review_document_state(db,invite_id)
        if not state:return None
        policy=self._review_policy(db,invite_id)
        unresolved=int(db.execute("SELECT COUNT(*) count FROM invitation_comments WHERE invitation_id=? AND parent_id='' AND resolved=0",(invite_id,)).fetchone()["count"] or 0)
        valid=int(db.execute("SELECT COUNT(DISTINCT decided_by) count FROM approval_requests WHERE invitation_id=? AND status='approved' AND decided_by<>'' AND decided_by<>requested_by AND document_revision=? AND document_fingerprint=?",(invite_id,state["revision"],state["fingerprint"])).fetchone()["count"] or 0)
        pending=int(db.execute("SELECT COUNT(*) count FROM approval_requests WHERE invitation_id=? AND status='pending' AND document_revision=? AND document_fingerprint=?",(invite_id,state["revision"],state["fingerprint"])).fetchone()["count"] or 0)
        blockers=[]
        if policy["approvalGate"] and valid<policy["minApprovals"]:blockers.append({"code":"approval_required","message":f"{policy['minApprovals']-valid} more current approval(s) required"})
        if policy["unresolvedCommentsGate"] and unresolved>0:blockers.append({"code":"unresolved_comments","message":f"Resolve {unresolved} open review comment(s)"})
        return {"ready":not blockers,"policy":policy,"revision":state["revision"],"fingerprint":state["fingerprint"],"validApprovals":valid,"pendingApprovals":pending,"unresolvedComments":unresolved,"blockers":blockers}

    def _review_participants(self,db,invite_id):
        rows=db.execute("SELECT owner_id user_id FROM invitations WHERE id=? UNION SELECT user_id FROM invitation_collaborators WHERE invitation_id=?",(invite_id,invite_id)).fetchall()
        return {str(row["user_id"]) for row in rows if row["user_id"]}

    def _review_notify(self,db,invite_id,actor_id,kind,target_id,message,recipients):
        now=int(time.time()*1000);created=0
        allowed=self._review_participants(db,invite_id)
        for user_id in sorted({str(value) for value in recipients if value and str(value)!=str(actor_id)} & allowed):
            db.execute("INSERT INTO review_notifications(id,invitation_id,user_id,actor_id,kind,target_id,message,read_at,created_at) VALUES(?,?,?,?,?,?,?,NULL,?)",(str(uuid.uuid4()),invite_id,user_id,str(actor_id or ''),str(kind)[:60],str(target_id or '')[:120],str(message or '')[:500],now));created+=1
        for user_id in sorted({str(value) for value in recipients if value and str(value)!=str(actor_id)} & allowed):
            db.execute("DELETE FROM review_notifications WHERE invitation_id=? AND user_id=? AND id NOT IN (SELECT id FROM review_notifications WHERE invitation_id=? AND user_id=? ORDER BY created_at DESC LIMIT 500)",(invite_id,user_id,invite_id,user_id))
        return created

    def review_context(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            role=self.invitation_role(db,invite_id,user["id"])
            if role is None:return self.json(404,{"error":"Invitation not found"})
            readiness=self._review_readiness(db,invite_id)
            rows=db.execute("SELECT n.*,u.email actor_email FROM review_notifications n LEFT JOIN users u ON u.id=n.actor_id WHERE n.invitation_id=? AND n.user_id=? ORDER BY n.created_at DESC LIMIT 100",(invite_id,user["id"])).fetchall()
            unread_count=int(db.execute("SELECT COUNT(*) count FROM review_notifications WHERE invitation_id=? AND user_id=? AND read_at IS NULL",(invite_id,user["id"])).fetchone()["count"] or 0)
            reviewer_rows=db.execute("SELECT u.id,u.email,'owner' role FROM invitations i JOIN users u ON u.id=i.owner_id WHERE i.id=? UNION ALL SELECT u.id,u.email,c.role FROM invitation_collaborators c JOIN users u ON u.id=c.user_id WHERE c.invitation_id=? ORDER BY role,email",(invite_id,invite_id)).fetchall()
        notifications=[]
        for row in rows:
            item=dict(row);item["read"]=bool(item.get("read_at"));notifications.append(item)
        self.json(200,{"role":role,"canManage":role in {"owner","manager"},"canEdit":role in {"owner","content","designer","manager"},"readiness":readiness,"notifications":notifications,"unreadCount":unread_count,"reviewers":[{"id":row["id"],"email":row["email"],"role":row["role"]} for row in reviewer_rows]})

    def update_review_policy(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);approval_gate=1 if data.get("approvalGate",False) else 0;comment_gate=1 if data.get("unresolvedCommentsGate",False) else 0
        try:min_approvals=max(1,min(5,int(data.get("minApprovals",1))))
        except (TypeError,ValueError):raise ValueError("Invalid minimum approval count")
        now=int(time.time()*1000)
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Management permission required"})
            db.execute("INSERT INTO invitation_review_policies(invitation_id,approval_gate,unresolved_comments_gate,min_approvals,updated_by,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(invitation_id) DO UPDATE SET approval_gate=excluded.approval_gate,unresolved_comments_gate=excluded.unresolved_comments_gate,min_approvals=excluded.min_approvals,updated_by=excluded.updated_by,updated_at=excluded.updated_at",(invite_id,approval_gate,comment_gate,min_approvals,user["id"],now))
            recipients=self._review_participants(db,invite_id)
            self._review_notify(db,invite_id,user["id"],"policy.updated",invite_id,"Review publishing policy was updated",recipients)
            readiness=self._review_readiness(db,invite_id)
        self.audit("review.policy_updated","invitation",invite_id,{"approvalGate":bool(approval_gate),"unresolvedCommentsGate":bool(comment_gate),"minApprovals":min_approvals})
        self.json(200,{"policy":readiness["policy"],"readiness":readiness})

    def mark_review_notifications(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(100_000);ids=data.get("ids",[]);ids=ids if isinstance(ids,list) else [];now=int(time.time()*1000)
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            if data.get("all",False):changed=db.execute("UPDATE review_notifications SET read_at=? WHERE invitation_id=? AND user_id=? AND read_at IS NULL",(now,invite_id,user["id"])).rowcount
            else:
                cleaned=[str(value)[:120] for value in ids[:100] if value]
                changed=0
                for notification_id in cleaned:changed+=db.execute("UPDATE review_notifications SET read_at=? WHERE id=? AND invitation_id=? AND user_id=? AND read_at IS NULL",(now,notification_id,invite_id,user["id"])).rowcount
        self.json(200,{"updated":int(changed or 0),"readAt":now})

    def list_review_tasks(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT t.*,u.email assignee_email,uu.email updated_by_email FROM review_tasks t LEFT JOIN users u ON u.id=t.assignee_id LEFT JOIN users uu ON uu.id=t.updated_by WHERE t.invitation_id=? ORDER BY CASE t.priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,CASE WHEN t.due_date='' THEN '9999-12-31' ELSE t.due_date END,t.updated_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(row) for row in rows])

    def update_review_task(self,invite_id,comment_id):
        user=self.require_user()
        if not user:return
        data=self.body(30_000);priority=str(data.get("priority","normal")).strip().lower();status=str(data.get("status","open")).strip().lower();due_date=str(data.get("dueDate","")).strip()[:10];assignee=str(data.get("assignee","")).strip()[:254]
        if priority not in {"low","normal","high"}:raise ValueError("Invalid review-task priority")
        if status not in {"open","in-progress","blocked","resolved"}:raise ValueError("Invalid review-task status")
        if due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",due_date):raise ValueError("Invalid review-task due date")
        now=int(time.time()*1000)
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            comment=db.execute("SELECT id,parent_id,resolved FROM invitation_comments WHERE id=? AND invitation_id=?",(comment_id,invite_id)).fetchone()
            if not comment:return self.json(404,{"error":"Comment not found"})
            root_id=str(comment["parent_id"] or comment["id"])
            if root_id!=comment_id:
                root=db.execute("SELECT id,resolved FROM invitation_comments WHERE id=? AND invitation_id=?",(root_id,invite_id)).fetchone()
                if not root:return self.json(404,{"error":"Comment thread not found"})
            assignee_id='';assignee_email=''
            if assignee:
                target=db.execute("SELECT u.id,u.email FROM users u WHERE (u.id=? OR lower(u.email)=lower(?)) AND u.id IN (SELECT owner_id FROM invitations WHERE id=? UNION SELECT user_id FROM invitation_collaborators WHERE invitation_id=?) LIMIT 1",(assignee,assignee,invite_id,invite_id)).fetchone()
                if not target:raise ValueError("Assignee must be an invitation owner or collaborator")
                assignee_id=str(target["id"]);assignee_email=str(target["email"])
            if not assignee_id and not due_date and priority=='normal' and status=='open':
                db.execute("DELETE FROM review_tasks WHERE invitation_id=? AND comment_id=?",(invite_id,root_id));result={"comment_id":root_id,"invitation_id":invite_id,"assignee_id":"","assignee_email":"","due_date":"","priority":"normal","status":"open","updated_by":user["id"],"updated_at":now}
            else:
                db.execute("INSERT INTO review_tasks(comment_id,invitation_id,assignee_id,due_date,priority,status,updated_by,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(comment_id) DO UPDATE SET assignee_id=excluded.assignee_id,due_date=excluded.due_date,priority=excluded.priority,status=excluded.status,updated_by=excluded.updated_by,updated_at=excluded.updated_at",(root_id,invite_id,assignee_id,due_date,priority,status,user["id"],now))
                result={"comment_id":root_id,"invitation_id":invite_id,"assignee_id":assignee_id,"assignee_email":assignee_email,"due_date":due_date,"priority":priority,"status":status,"updated_by":user["id"],"updated_at":now}
                if assignee_id:self._review_notify(db,invite_id,user["id"],"task.assigned",root_id,f"{user['email']} assigned a review task to {assignee_email}",{assignee_id})
        self.audit("review.task_updated","comment",root_id,{"invitationId":invite_id,"assignee":assignee_email,"dueDate":due_date,"priority":priority,"status":status})
        self.json(200,result)

    def get_comments(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT c.*,u.email FROM invitation_comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.invitation_id=? ORDER BY CASE WHEN c.parent_id='' THEN c.created_at ELSE COALESCE((SELECT p.created_at FROM invitation_comments p WHERE p.id=c.parent_id),c.created_at) END,CASE WHEN c.parent_id='' THEN 0 ELSE 1 END,c.created_at",(invite_id,)).fetchall()
            can_manage=self.can_manage_invitation(db,invite_id,user["id"])
        result=[]
        for row in rows:
            item=dict(row);item["resolved"]=bool(item.get("resolved"));item["canDelete"]=bool(item.get("user_id")==user["id"] or can_manage);result.append(item)
        self.json(200,result)

    def add_comment(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);body=str(data.get("body","")).strip()[:2000]
        if not body:raise ValueError("Comment is required")
        object_id=str(data.get("objectId","")).strip()[:120];page_id=str(data.get("pageId","")).strip()[:120];parent_id=str(data.get("parentId","")).strip()[:120]
        def anchor_value(name):
            try:value=float(data.get(name,-1))
            except (TypeError,ValueError):value=-1
            return max(0.0,min(1.0,value)) if value>=0 else -1.0
        anchor_x=anchor_value("anchorX");anchor_y=anchor_value("anchorY")
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            if parent_id:
                parent=db.execute("SELECT id,parent_id,object_id,page_id,anchor_x,anchor_y FROM invitation_comments WHERE id=? AND invitation_id=?",(parent_id,invite_id)).fetchone()
                if not parent:raise ValueError("Comment thread was not found")
                parent_id=parent["parent_id"] or parent["id"];object_id=parent["object_id"] or object_id;page_id=parent["page_id"] or page_id;anchor_x=float(parent["anchor_x"]);anchor_y=float(parent["anchor_y"])
            cid=str(uuid.uuid4());now=int(time.time()*1000)
            db.execute("INSERT INTO invitation_comments(id,invitation_id,user_id,object_id,page_id,parent_id,anchor_x,anchor_y,body,resolved,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,0,?,?)",(cid,invite_id,user["id"],object_id,page_id,parent_id,anchor_x,anchor_y,body,now,now))
            if parent_id:
                recipients={row["user_id"] for row in db.execute("SELECT DISTINCT user_id FROM invitation_comments WHERE invitation_id=? AND (id=? OR parent_id=?)",(invite_id,parent_id,parent_id)).fetchall()}
                message=f"{user['email']} replied to a review comment"
                kind="comment.replied"
            else:
                recipients=self._review_participants(db,invite_id);message=f"{user['email']} added a review comment";kind="comment.added"
            self._review_notify(db,invite_id,user["id"],kind,cid,message,recipients)
        self.audit("comment.added","comment",cid,{"invitationId":invite_id,"pageId":page_id,"objectId":object_id,"parentId":parent_id})
        self.json(201,{"id":cid,"invitation_id":invite_id,"user_id":user["id"],"email":user["email"],"object_id":object_id,"page_id":page_id,"parent_id":parent_id,"anchor_x":anchor_x,"anchor_y":anchor_y,"body":body,"resolved":False,"created_at":now,"updated_at":now,"canDelete":True})

    def resolve_comment(self,invite_id,comment_id):
        user=self.require_user()
        if not user:return
        data=self.body(10_000);resolved=1 if data.get("resolved",True) else 0
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            row=db.execute("SELECT id,parent_id FROM invitation_comments WHERE id=? AND invitation_id=?",(comment_id,invite_id)).fetchone()
            if not row:return self.json(404,{"error":"Comment not found"})
            root_id=row["parent_id"] or row["id"]
            changed=db.execute("UPDATE invitation_comments SET resolved=?,updated_at=? WHERE id=? AND invitation_id=?",(resolved,int(time.time()*1000),root_id,invite_id)).rowcount
            recipients={item["user_id"] for item in db.execute("SELECT DISTINCT user_id FROM invitation_comments WHERE invitation_id=? AND (id=? OR parent_id=?)",(invite_id,root_id,root_id)).fetchall()}
            self._review_notify(db,invite_id,user["id"],"comment.resolved" if resolved else "comment.reopened",root_id,f"{user['email']} {'resolved' if resolved else 'reopened'} a review comment",recipients)
        self.audit("comment.resolved" if resolved else "comment.reopened","comment",root_id,{"invitationId":invite_id})
        self.json(200 if changed else 404,{"id":root_id,"resolved":bool(resolved)})

    def delete_comment(self,invite_id,comment_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT id,parent_id,user_id FROM invitation_comments WHERE id=? AND invitation_id=?",(comment_id,invite_id)).fetchone()
            if not row:return self.json(404,{"error":"Comment not found"})
            if row["user_id"]!=user["id"] and not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Only the author or a manager can delete this comment"})
            if row["parent_id"]:changed=db.execute("DELETE FROM invitation_comments WHERE id=? AND invitation_id=?",(comment_id,invite_id)).rowcount
            else:
                db.execute("DELETE FROM review_tasks WHERE invitation_id=? AND comment_id=?",(invite_id,comment_id))
                changed=db.execute("DELETE FROM invitation_comments WHERE invitation_id=? AND (id=? OR parent_id=?)",(invite_id,comment_id,comment_id)).rowcount
        self.audit("comment.deleted","comment",comment_id,{"invitationId":invite_id})
        self.json(200,{"deleted":bool(changed)})

    def list_approvals(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            invite=db.execute("SELECT updated_at,draft_json FROM invitations WHERE id=?",(invite_id,)).fetchone()
            rows=db.execute("SELECT a.*,u.email requester_email,du.email decider_email FROM approval_requests a LEFT JOIN users u ON u.id=a.requested_by LEFT JOIN users du ON du.id=a.decided_by WHERE a.invitation_id=? ORDER BY a.created_at DESC",(invite_id,)).fetchall()
        current_revision=int(invite["updated_at"] or 0) if invite else 0;current_fingerprint=hashlib.sha256(str(invite["draft_json"] or "{}").encode()).hexdigest()[:24] if invite else ""
        result=[]
        for row in rows:
            item=dict(row)
            try:item["summary"]=json.loads(item.get("summary_json") or "{}")
            except Exception:item["summary"]={}
            item["stale"]=bool(item.get("document_revision") and (int(item.get("document_revision") or 0)!=current_revision or item.get("document_fingerprint")!=current_fingerprint));result.append(item)
        self.json(200,result)

    def request_approval(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);requested_from=str(data.get("requestedFrom","")).strip()[:254];note=str(data.get("note","")).strip()[:2000];now=int(time.time()*1000);approval_id=str(uuid.uuid4())
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            invite=db.execute("SELECT updated_at,draft_json FROM invitations WHERE id=?",(invite_id,)).fetchone()
            if not invite:return self.json(404,{"error":"Invitation not found"})
            raw=str(invite["draft_json"] or "{}");revision=int(invite["updated_at"] or 0);fingerprint=hashlib.sha256(raw.encode()).hexdigest()[:24]
            try:document=json.loads(raw)
            except Exception:document={}
            pages=document.get("designPages") if isinstance(document.get("designPages"),list) else []
            objects=document.get("objects") if isinstance(document.get("objects"),dict) else {}
            summary={"title":str((document.get("fields") or {}).get("names") or "Invitation")[:160],"pages":1+len(pages),"objects":len(objects)}
            db.execute("INSERT INTO approval_requests(id,invitation_id,requested_by,requested_from,status,note,document_revision,document_fingerprint,summary_json,decided_by,decided_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,'',NULL,?,?)",(approval_id,invite_id,user["id"],requested_from,"pending",note,revision,fingerprint,json.dumps(summary,separators=(',',':')),now,now))
            recipients=set()
            if requested_from:
                target=db.execute("SELECT id FROM users WHERE lower(email)=lower(?) OR id=? LIMIT 1",(requested_from,requested_from)).fetchone()
                if target:recipients.add(target["id"])
            if not recipients:
                recipients={row["user_id"] for row in db.execute("SELECT owner_id user_id FROM invitations WHERE id=? UNION SELECT user_id FROM invitation_collaborators WHERE invitation_id=? AND role='manager'",(invite_id,invite_id)).fetchall()}
            self._review_notify(db,invite_id,user["id"],"approval.requested",approval_id,f"{user['email']} requested approval for the current design",recipients)
        self.audit("approval.requested","approval",approval_id,{"invitationId":invite_id,"requestedFrom":requested_from,"revision":revision})
        self.json(201,{"id":approval_id,"requested_from":requested_from,"status":"pending","note":note,"document_revision":revision,"document_fingerprint":fingerprint,"summary":summary,"stale":False,"created_at":now,"updated_at":now})

    def decide_approval(self,invite_id,approval_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);status=str(data.get("status","approved")).lower()
        if status not in {"approved","changes-requested","cancelled"}:raise ValueError("Invalid approval status")
        decision_note=str(data.get("note","")).strip()[:2000];now=int(time.time()*1000)
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT requested_by,requested_from FROM approval_requests WHERE id=? AND invitation_id=?",(approval_id,invite_id)).fetchone()
            if not row:return self.json(404,{"error":"Approval request not found"})
            identity={str(user["id"]).lower(),str(user["email"]).lower()}
            is_manager=self.can_manage_invitation(db,invite_id,user["id"]);is_reviewer=bool(row["requested_from"]) and str(row["requested_from"]).lower() in identity;is_requester=row["requested_by"]==user["id"]
            allowed=is_manager or is_reviewer or (status=="cancelled" and is_requester)
            if not allowed:return self.json(403,{"error":"Only the assigned reviewer or an invitation manager can decide this approval request"})
            db.execute("UPDATE approval_requests SET status=?,note=CASE WHEN ?<>'' THEN ? ELSE note END,decided_by=?,decided_at=?,updated_at=? WHERE id=?",(status,decision_note,decision_note,user["id"],now,now,approval_id))
            self._review_notify(db,invite_id,user["id"],"approval.decided",approval_id,f"{user['email']} marked an approval request as {status.replace('-', ' ')}",{row["requested_by"]})
        self.audit("approval.decided","approval",approval_id,{"invitationId":invite_id,"status":status})
        self.json(200,{"id":approval_id,"status":status,"decided_by":user["id"],"decided_at":now})

    def get_guests(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            rows=db.execute("SELECT g.id,g.name,g.phone,g.email,g.group_name,g.household_id,g.tags_json,g.table_name,g.seat_label,g.delivery_status,g.opened_at,g.token_salt,g.token_version,g.token_expires_at,g.token_revoked_at,g.created_at,g.checked_in,g.checked_in_at,(SELECT status FROM rsvps r WHERE r.invitation_id=g.invitation_id AND lower(r.name)=lower(g.name) ORDER BY created_at DESC LIMIT 1) rsvp_status FROM guests g WHERE g.invitation_id=? ORDER BY g.created_at DESC",(invite_id,)).fetchall()
        result=[]
        for row in rows:
            item=dict(row);token=None
            if item.get("token_salt") and not item.get("token_revoked_at") and (not item.get("token_expires_at") or item["token_expires_at"]>int(time.time()*1000)):
                token=guest_token_value(item["id"],item["token_salt"],item.get("token_version") or 1)
            item["token"]=token;item["personalLinkAvailable"]=bool(token);
            try:item["tags"]=json.loads(item.pop("tags_json") or "[]")
            except Exception:item["tags"]=[]
            result.append(item)
        self.json(200,result)

    def add_guest(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(100_000);name=str(data.get("name","")).strip()[:120]
        if not name:raise ValueError("Guest name is required")
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            guest_id=str(uuid.uuid4());salt=secrets.token_urlsafe(18);version=1;token=guest_token_value(guest_id,salt,version);token_hash=guest_token_hash(token);expires=None
            days=data.get("linkExpiresDays")
            if days not in (None,""):
                try:days=max(1,min(3650,int(days)));expires=int(time.time()*1000)+days*24*60*60*1000
                except (TypeError,ValueError):raise ValueError("Invalid personal-link expiration")
            # The legacy token column remains as a non-secret compatibility key only.
            sentinel="hashed-"+guest_id
            tags=data.get("tags",[]);tags=tags if isinstance(tags,list) else []
            db.execute("INSERT INTO guests(id,invitation_id,name,phone,email,group_name,household_id,tags_json,table_name,seat_label,token,token_hash,token_salt,token_version,token_expires_at,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(guest_id,invite_id,name,str(data.get("phone","")).strip()[:40],str(data.get("email","")).strip()[:254],str(data.get("groupName","")).strip()[:80],str(data.get("householdId","")).strip()[:80],json.dumps([str(x)[:50] for x in tags[:20]],ensure_ascii=False),str(data.get("tableName","")).strip()[:80],str(data.get("seatLabel","")).strip()[:40],sentinel,token_hash,salt,version,expires,int(time.time()*1000)))
        self.json(201,{"id":guest_id,"name":name,"token":token,"tokenExpiresAt":expires})

    def rotate_guest_token(self,invite_id,guest_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);expires=None
        days=data.get("expiresDays")
        if days not in (None,""):
            try:days=max(1,min(3650,int(days)));expires=int(time.time()*1000)+days*24*60*60*1000
            except (TypeError,ValueError):raise ValueError("Invalid personal-link expiration")
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT id,token_version FROM guests WHERE id=? AND invitation_id=?",(guest_id,invite_id)).fetchone()
            if not row:return self.json(404,{"error":"Guest not found"})
            salt=secrets.token_urlsafe(18);version=int(row["token_version"] or 0)+1;token=guest_token_value(guest_id,salt,version)
            db.execute("UPDATE guests SET token_hash=?,token_salt=?,token_version=?,token_expires_at=?,token_revoked_at=NULL WHERE id=? AND invitation_id=?",(guest_token_hash(token),salt,version,expires,guest_id,invite_id))
        self.json(200,{"token":token,"tokenExpiresAt":expires,"rotated":True})

    def revoke_guest_token(self,invite_id,guest_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            changed=db.execute("UPDATE guests SET token_revoked_at=? WHERE id=? AND invitation_id=?",(int(time.time()*1000),guest_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"revoked":bool(changed)})

    def delete_guest(self,invite_id,guest_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            changed=db.execute("DELETE FROM guests WHERE id=? AND invitation_id=?",(guest_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})
    def check_in_guest(self,invite_id,guest_id):
        user=self.require_user()
        if not user:return
        data=self.body(10_000);checked=1 if data.get("checkedIn",True) else 0
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            row=db.execute("SELECT checked_in,checked_in_at FROM guests WHERE id=? AND invitation_id=?",(guest_id,invite_id)).fetchone()
            if not row:return self.json(404,{"error":"Guest not found"})
            already=bool(row["checked_in"]) and bool(checked)
            checked_at=int(row["checked_in_at"] or 0) if already else (int(time.time()*1000) if checked else None)
            db.execute("UPDATE guests SET checked_in=?,checked_in_at=? WHERE id=? AND invitation_id=?",(checked,checked_at,guest_id,invite_id))
        self.json(200,{"checkedIn":bool(checked),"checkedInAt":checked_at,"alreadyCheckedIn":already})
    def public_action_publication(self, db, slug, access_token=None):
        row=db.execute("SELECT i.id invitation_id,i.access_mode,p.id publication_id,p.document_json FROM invitations i JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? AND i.is_published=1 AND i.archived=0 AND i.deleted_at IS NULL AND (i.expires_at IS NULL OR i.expires_at>?) ORDER BY p.published_at DESC LIMIT 1",(slug,int(time.time()*1000))).fetchone()
        if not row:
            self.json(404,{"error":"Published invitation not found"});return None
        if row["access_mode"]=="password" and not self.access_token_valid(db,row["invitation_id"],access_token):
            self.json(403,{"error":"Invitation access is required","protected":True});return None
        return row

    def submit_wish(self, slug):
        if not self.rate_limit(f"wish:{self.client_address[0]}:{slug}",10,60):return
        data=self.body(100_000);name=str(data.get("name","")).strip()[:120];message=str(data.get("message","")).strip()[:2000];access_token=self.headers.get("X-Invitation-Access") or data.get("accessToken")
        if not self.bot_protection_ok("guest-wish",data.get("botToken","")):return self.json(403,{"error":"Submission verification failed"})
        if str(data.get("website","")).strip():return self.json(400,{"error":"Invalid submission"})
        if not name or not message:raise ValueError("Name and message are required")
        with connect() as db:
            pub=self.public_action_publication(db,slug,access_token)
            if not pub:return
            document=json.loads(pub["document_json"])
            if document.get("settings",{}).get("wishesEnabled") is not True:return self.json(403,{"error":"Guest wishes are not enabled for this invitation"})
            item_id=str(uuid.uuid4());db.execute("INSERT INTO guest_messages VALUES(?,?,?,?,?,?)",(item_id,pub["invitation_id"],pub["publication_id"],name,message,int(time.time()*1000)))
        self.json(201,{"id":item_id,"saved":True})

    def get_wishes(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,name,message,created_at FROM guest_messages WHERE invitation_id=? ORDER BY created_at DESC",(invite_id,)).fetchall()
        self.json(200,[{"id":r["id"],"name":r["name"],"message":r["message"],"createdAt":r["created_at"]} for r in rows])

    def delete_wish(self,invite_id,wish_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            changed=db.execute("DELETE FROM guest_messages WHERE id=? AND invitation_id=?",(wish_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def rsvp(self, slug):
        if not self.rate_limit(f"rsvp:{self.client_address[0]}:{slug}",12,60): return
        data=self.body(100_000);name=str(data.get("name","")).strip()[:120];access_token=self.headers.get("X-Invitation-Access") or data.get("accessToken");guest_token=self.headers.get("X-Invitation-Guest") or data.get("guestToken")
        if not self.bot_protection_ok("rsvp",data.get("botToken","")):return self.json(403,{"error":"Submission verification failed"})
        if str(data.get("website","")).strip():return self.json(400,{"error":"Invalid submission"})
        if not name:raise ValueError("Name is required")
        status=str(data.get("status","Maybe"))[:40]
        if status not in {"Yes, joyfully","Unable to attend","Maybe"}:raise ValueError("Invalid RSVP status")
        with connect() as db:
            pub=self.public_action_publication(db,slug,access_token)
            if not pub:return
            document=json.loads(pub["document_json"]);settings=document.get("settings",{})
            if settings.get("rsvpEnabled") is False:return self.json(403,{"error":"RSVP is not enabled for this invitation"})
            close_date=str(settings.get("rsvpCloseDate") or "").strip()
            if close_date:
                try:
                    closed_at=time.mktime(time.strptime(close_date[:10],"%Y-%m-%d"))+24*60*60
                    if time.time()>=closed_at:return self.json(410,{"error":"RSVP is closed for this invitation","code":"rsvp_closed"})
                except ValueError:pass
            max_guests=max(1,min(50,int(settings.get("rsvpMaxGuests") or 10)))
            try:count=max(1,min(max_guests,int(data.get("count",1))))
            except (TypeError,ValueError):raise ValueError("Invalid guest count")
            answers={k:str(v).strip()[:2000] for k,v in data.items() if str(k).startswith("custom_") or k in {"meal","transport","accommodation"}}
            if len(answers)>24:raise ValueError("Too many RSVP answers")
            for field in document.get("rsvpFields",[]) or []:
                key="custom_"+re.sub(r"[^A-Za-z0-9_-]","",str(field.get("id","")));value=answers.get(key,"")
                if field.get("required") and not value:raise ValueError(f"Required RSVP field is missing: {field.get('label','Question')}")
                if value and field.get("type")=="select" and value not in (field.get("options") or []):raise ValueError("Invalid RSVP option")
                if value and field.get("type")=="number":
                    try:float(value)
                    except ValueError:raise ValueError("Invalid numeric RSVP answer")
            guest=None
            if guest_token:guest=self.lookup_guest_by_token(db,pub["invitation_id"],guest_token)
            guest_id=guest["id"] if guest else None;normalized=re.sub(r"\s+"," ",name.lower()).strip();now=int(time.time()*1000);note=str(data.get("note",""))[:1000]
            existing=None
            if guest_id:existing=db.execute("SELECT id FROM rsvps WHERE invitation_id=? AND guest_id=? LIMIT 1",(pub["invitation_id"],guest_id)).fetchone()
            if not existing:
                existing=db.execute("SELECT id FROM rsvps WHERE invitation_id=? AND publication_id=? AND guest_id IS NULL AND normalized_name=? AND created_at>? ORDER BY created_at DESC LIMIT 1",(pub["invitation_id"],pub["publication_id"],normalized,now-10*60*1000)).fetchone()
            if existing:
                rid=existing["id"];db.execute("UPDATE rsvps SET publication_id=?,guest_id=COALESCE(guest_id,?),name=?,normalized_name=?,status=?,guest_count=?,note=?,updated_at=?,answers_json=? WHERE id=?",(pub["publication_id"],guest_id,name,normalized,status,count,note,now,json.dumps(answers,ensure_ascii=False),rid));updated=True
            else:
                rid=str(uuid.uuid4());db.execute("INSERT INTO rsvps(id,invitation_id,publication_id,guest_id,name,normalized_name,status,guest_count,note,created_at,updated_at,answers_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(rid,pub["invitation_id"],pub["publication_id"],guest_id,name,normalized,status,count,note,now,now,json.dumps(answers,ensure_ascii=False)));updated=False
        self.json(200 if updated else 201,{"id":rid,"saved":True,"updated":updated})

    def get_rsvps(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            rows=db.execute("SELECT * FROM rsvps WHERE invitation_id=? ORDER BY created_at DESC",(invite_id,)).fetchall()
        result=[]
        for r in rows:
            item=dict(r);item["answers"]=json.loads(item.pop("answers_json","{}") or "{}");result.append(item)
        self.json(200,result)
    def update_rsvp(self,invite_id,rsvp_id):
        user=self.require_user()
        if not user:return
        data=self.body(100_000);status=str(data.get("status",""))[:40]
        if status not in {"Yes, joyfully","Unable to attend","Maybe"}:raise ValueError("Invalid RSVP status")
        try:count=max(1,min(10,int(data.get("guestCount",1))))
        except (TypeError,ValueError):raise ValueError("Invalid guest count")
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            changed=db.execute("UPDATE rsvps SET status=?,guest_count=? WHERE id=? AND invitation_id=?",(status,count,rsvp_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"updated":bool(changed),"status":status,"guestCount":count})

    def delete_rsvp(self,invite_id,rsvp_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            changed=db.execute("DELETE FROM rsvps WHERE id=? AND invitation_id=?",(rsvp_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def configure_rsvp(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000)
        if not isinstance(data.get("enabled"),bool):raise ValueError("RSVP enabled must be boolean")
        enabled=bool(data["enabled"]);now=int(time.time()*1000)
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            row=db.execute("SELECT draft_json FROM invitations WHERE id=? AND deleted_at IS NULL",(invite_id,)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            draft=validate_document(json.loads(row["draft_json"] or "{}"));draft["settings"]={**(draft.get("settings") or {}),"rsvpEnabled":enabled}
            db.execute("UPDATE invitations SET draft_json=?,updated_at=?,last_client_id=NULL,last_mutation_id=NULL WHERE id=?",(json.dumps(draft,ensure_ascii=False),now,invite_id))
        self.audit("invitation.rsvp_configured","invitation",invite_id,{"enabled":enabled})
        self.json(200,{"enabled":enabled})

    def ai_guest_delivery_status(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(30_000);guest_ids=data.get("guestIds") or []
        if not isinstance(guest_ids,list) or len(guest_ids)>100:raise ValueError("Invalid guest ID list")
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            rows=db.execute("SELECT id,name,delivery_status,opened_at,checked_in,checked_in_at FROM guests WHERE invitation_id=? ORDER BY created_at DESC LIMIT 500",(invite_id,)).fetchall()
        allowed={str(x) for x in guest_ids if str(x)}
        delivery=[{"guestId":r["id"],"name":r["name"],"deliveryStatus":r["delivery_status"],"openedAt":r["opened_at"],"checkedIn":bool(r["checked_in"]),"checkedInAt":r["checked_in_at"]} for r in rows if not allowed or r["id"] in allowed]
        self.json(200,{"delivery":delivery[:500]})

    def get_versions(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,version,published_at,length(document_json) document_bytes FROM publications WHERE invitation_id=? ORDER BY published_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(r) for r in rows])

    def get_version(self,invite_id,version):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT id,version,published_at,document_json FROM publications WHERE invitation_id=? AND (id=? OR CAST(version AS TEXT)=?) ORDER BY published_at DESC LIMIT 1",(invite_id,str(version),str(version))).fetchone()
        if not row:return self.json(404,{"error":"Published version not found"})
        self.json(200,{"id":row["id"],"version":row["version"],"publishedAt":row["published_at"],"document":json.loads(row["document_json"])})

    def restore_published_version(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);version=str(data.get("version") or data.get("id") or "").strip()
        if not version:raise ValueError("Published version is required")
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            row=db.execute("SELECT document_json FROM publications WHERE invitation_id=? AND (id=? OR CAST(version AS TEXT)=?) ORDER BY published_at DESC LIMIT 1",(invite_id,version,version)).fetchone()
            if not row:return self.json(404,{"error":"Published version not found"})
            document=validate_document(json.loads(row["document_json"]));now=int(time.time()*1000)
            db.execute("UPDATE invitations SET draft_json=?,updated_at=?,last_client_id=NULL,last_mutation_id=NULL WHERE id=?",(json.dumps(document,ensure_ascii=False),now,invite_id))
        self.audit("invitation.version_restored","invitation",invite_id,{"version":version})
        self.json(200,{"restored":True,"updatedAt":now,"document":document})

    def template_payload(self, row, include_document=True):
        value={
            "id":row["id"],"name":row["name"],"category":row["category"],
            "description":row["description"] or "","tags":json.loads(row["tags_json"] or "[]"),
            "favorite":bool(row["favorite"]),"currentVersion":int(row["current_version"] or 1),
            "thumbnail":json.loads(row["thumbnail_json"] or "{}"),
            "visibility":row["visibility"] if "visibility" in row.keys() else "private",
            "publishedAt":row["published_at"] if "published_at" in row.keys() else None,
            "marketplaceStatus":row["marketplace_status"] if "marketplace_status" in row.keys() else ("approved" if row["visibility"]=="public" else "draft"),
            "licenseType":row["license_type"] if "license_type" in row.keys() else "personal",
            "createdAt":row["created_at"],"updatedAt":row["updated_at"]
        }
        if include_document:value["document"]=json.loads(row["document_json"])
        return value

    def template_metadata(self, data, existing=None):
        name=str(data.get("name", existing["name"] if existing else "")).strip()[:120]
        if not name: raise ValueError("Template name is required")
        category=str(data.get("category", existing["category"] if existing else "Wedding")).strip()[:40] or "Other"
        description=str(data.get("description", existing["description"] if existing else "")).strip()[:500]
        raw_tags=data.get("tags", json.loads(existing["tags_json"] or "[]") if existing else [])
        if not isinstance(raw_tags,list): raise ValueError("Template tags must be a list")
        tags=[]
        for item in raw_tags[:20]:
            tag=str(item).strip()[:40]
            if tag and tag not in tags: tags.append(tag)
        favorite=1 if data.get("favorite", bool(existing["favorite"]) if existing else False) else 0
        thumbnail=data.get("thumbnail", json.loads(existing["thumbnail_json"] or "{}") if existing else {})
        if not isinstance(thumbnail,dict) or len(json.dumps(thumbnail))>50_000: raise ValueError("Invalid template thumbnail metadata")
        license_type=str(data.get("licenseType", existing["license_type"] if existing is not None and "license_type" in existing.keys() else "personal")).strip().lower()
        if license_type not in {"personal","commercial","extended"}: raise ValueError("Invalid template license")
        return name,category,description,json.dumps(tags,ensure_ascii=False),favorite,json.dumps(thumbnail,ensure_ascii=False),license_type

    def list_marketplace_templates(self):
        with connect() as db:
            rows=db.execute("SELECT * FROM user_templates WHERE visibility='public' AND marketplace_status='approved' ORDER BY published_at DESC,updated_at DESC LIMIT 300").fetchall()
        self.json(200,[self.template_payload(r) for r in rows])

    def get_marketplace_template(self,template_id):
        with connect() as db:row=db.execute("SELECT * FROM user_templates WHERE id=? AND visibility='public' AND marketplace_status='approved'",(template_id,)).fetchone()
        if not row:return self.json(404,{"error":"Marketplace template not found"})
        self.json(200,self.template_payload(row))

    def list_templates(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT * FROM user_templates WHERE owner_id=? ORDER BY favorite DESC,updated_at DESC LIMIT 200",(user["id"],)).fetchall()
        self.json(200,[self.template_payload(r) for r in rows])

    def get_template(self, template_id):
        user=self.require_user()
        if not user:return
        with connect() as db: row=db.execute("SELECT * FROM user_templates WHERE id=? AND owner_id=?",(template_id,user["id"])).fetchone()
        if not row:return self.json(404,{"error":"Template not found"})
        self.json(200,self.template_payload(row))

    def create_template(self):
        user=self.require_user()
        if not user:return
        if not self.require_plan_capacity(user,"templates"):return
        if not self.rate_limit(f"template:{user['id']}",60,3600): return
        data=self.body(); document=validate_document(data.get("document",{})); template_id=str(uuid.uuid4()); now=int(time.time()*1000)
        name,category,description,tags_json,favorite,thumbnail_json,license_type=self.template_metadata(data)
        with connect() as db:
            requested_visibility=str(data.get("visibility","private"));requested_visibility=requested_visibility if requested_visibility in {"private","public"} else "private"
            moderation=os.getenv("EINVITE_MARKETPLACE_REQUIRES_MODERATION","0")=="1" and (user["role"] if "role" in user.keys() else "customer")!="admin"
            marketplace_status="pending" if requested_visibility=="public" and moderation else ("approved" if requested_visibility=="public" else "draft")
            visibility="public" if requested_visibility=="public" and not moderation else "private";published_at=now if visibility=="public" else None
            db.execute("INSERT INTO user_templates(id,owner_id,name,category,document_json,created_at,updated_at,description,tags_json,favorite,current_version,thumbnail_json,visibility,published_at,marketplace_status,license_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(template_id,user["id"],name,category,json.dumps(document),now,now,description,tags_json,favorite,1,thumbnail_json,visibility,published_at,marketplace_status,license_type))
            db.execute("INSERT INTO template_versions(id,template_id,version,document_json,created_at) VALUES(?,?,?,?,?)",(str(uuid.uuid4()),template_id,1,json.dumps(document),now))
            row=db.execute("SELECT * FROM user_templates WHERE id=?",(template_id,)).fetchone()
        self.json(201,self.template_payload(row))

    def update_template(self, template_id):
        user=self.require_user()
        if not user:return
        data=self.body();now=int(time.time()*1000)
        with connect() as db:
            existing=db.execute("SELECT * FROM user_templates WHERE id=? AND owner_id=?",(template_id,user["id"])).fetchone()
            if not existing:return self.json(404,{"error":"Template not found"})
            name,category,description,tags_json,favorite,thumbnail_json,license_type=self.template_metadata(data,existing)
            requested_visibility=str(data.get("visibility",existing["visibility"] if "visibility" in existing.keys() else "private"))
            if requested_visibility not in {"private","public"}:raise ValueError("Invalid template visibility")
            existing_status=existing["marketplace_status"] if "marketplace_status" in existing.keys() else ("approved" if existing["visibility"]=="public" else "draft")
            moderation=os.getenv("EINVITE_MARKETPLACE_REQUIRES_MODERATION","0")=="1" and (user["role"] if "role" in user.keys() else "customer")!="admin"
            if requested_visibility=="public" and moderation and existing_status!="approved":
                visibility="private";marketplace_status="pending";published_at=None
            elif requested_visibility=="public":
                visibility="public";marketplace_status="approved";published_at=(existing["published_at"] if "published_at" in existing.keys() else None) or now
            else:
                visibility="private";marketplace_status="draft";published_at=None
            document_json=existing["document_json"];current_version=int(existing["current_version"] or 1)
            if "document" in data:
                document=validate_document(data["document"]);document_json=json.dumps(document);current_version+=1
                db.execute("INSERT INTO template_versions(id,template_id,version,document_json,created_at) VALUES(?,?,?,?,?)",(str(uuid.uuid4()),template_id,current_version,document_json,now))
            db.execute("UPDATE user_templates SET name=?,category=?,description=?,tags_json=?,favorite=?,thumbnail_json=?,document_json=?,current_version=?,visibility=?,published_at=?,marketplace_status=?,license_type=?,updated_at=? WHERE id=? AND owner_id=?",(name,category,description,tags_json,favorite,thumbnail_json,document_json,current_version,visibility,published_at,marketplace_status,license_type,now,template_id,user["id"]))
            row=db.execute("SELECT * FROM user_templates WHERE id=?",(template_id,)).fetchone()
        self.json(200,self.template_payload(row))

    def duplicate_template(self, template_id):
        user=self.require_user()
        if not user:return
        with connect() as db: source=db.execute("SELECT * FROM user_templates WHERE id=? AND owner_id=?",(template_id,user["id"])).fetchone()
        if not source:return self.json(404,{"error":"Template not found"})
        data={"name":f"{source['name']} Copy","category":source["category"],"description":source["description"],"tags":json.loads(source["tags_json"] or "[]"),"document":json.loads(source["document_json"]),"thumbnail":json.loads(source["thumbnail_json"] or "{}")}
        # Reuse validation/creation semantics without recursively parsing the request body.
        document=validate_document(data["document"]);new_id=str(uuid.uuid4());now=int(time.time()*1000)
        with connect() as db:
            db.execute("INSERT INTO user_templates(id,owner_id,name,category,document_json,created_at,updated_at,description,tags_json,favorite,current_version,thumbnail_json,visibility,published_at,marketplace_status,license_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(new_id,user["id"],data["name"],data["category"],json.dumps(document),now,now,data["description"],json.dumps(data["tags"],ensure_ascii=False),0,1,json.dumps(data["thumbnail"],ensure_ascii=False),"private",None,"draft",source["license_type"] if "license_type" in source.keys() else "personal"))
            db.execute("INSERT INTO template_versions(id,template_id,version,document_json,created_at) VALUES(?,?,?,?,?)",(str(uuid.uuid4()),new_id,1,json.dumps(document),now))
            row=db.execute("SELECT * FROM user_templates WHERE id=?",(new_id,)).fetchone()
        self.json(201,self.template_payload(row))

    def get_template_versions(self, template_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            owner=db.execute("SELECT 1 FROM user_templates WHERE id=? AND owner_id=?",(template_id,user["id"])).fetchone()
            if not owner:return self.json(404,{"error":"Template not found"})
            rows=db.execute("SELECT id,version,created_at FROM template_versions WHERE template_id=? ORDER BY version DESC",(template_id,)).fetchall()
        self.json(200,[{"id":r["id"],"version":r["version"],"createdAt":r["created_at"]} for r in rows])

    def restore_template_version(self, template_id):
        user=self.require_user()
        if not user:return
        data=self.body(100_000)
        try: version=int(data.get("version"))
        except (TypeError,ValueError): raise ValueError("Template version is required")
        now=int(time.time()*1000)
        with connect() as db:
            template=db.execute("SELECT * FROM user_templates WHERE id=? AND owner_id=?",(template_id,user["id"])).fetchone()
            if not template:return self.json(404,{"error":"Template not found"})
            old=db.execute("SELECT document_json FROM template_versions WHERE template_id=? AND version=?",(template_id,version)).fetchone()
            if not old:return self.json(404,{"error":"Template version not found"})
            document=validate_document(json.loads(old["document_json"]));new_version=int(template["current_version"] or 1)+1;document_json=json.dumps(document)
            db.execute("INSERT INTO template_versions(id,template_id,version,document_json,created_at) VALUES(?,?,?,?,?)",(str(uuid.uuid4()),template_id,new_version,document_json,now))
            db.execute("UPDATE user_templates SET document_json=?,current_version=?,updated_at=? WHERE id=? AND owner_id=?",(document_json,new_version,now,template_id,user["id"]))
            row=db.execute("SELECT * FROM user_templates WHERE id=?",(template_id,)).fetchone()
        self.json(200,self.template_payload(row))

    def list_page_templates(self):
        user=self.require_user()
        if not user:return
        with connect() as db: rows=db.execute("SELECT * FROM user_page_templates WHERE owner_id=? ORDER BY favorite DESC,updated_at DESC LIMIT 300",(user["id"],)).fetchall()
        self.json(200,[{"id":r["id"],"name":r["name"],"category":r["category"],"page":json.loads(r["page_json"]),"favorite":bool(r["favorite"]),"createdAt":r["created_at"],"updatedAt":r["updated_at"]} for r in rows])

    def validate_page_template(self, page):
        if not isinstance(page,dict):raise ValueError("Page template must be an object")
        page=dict(page);page_id=str(page.get("id") or f"page-{uuid.uuid4().hex[:12]}");page["id"]=re.sub(r"[^A-Za-z0-9_-]","-",page_id)[:120] or f"page-{uuid.uuid4().hex[:12]}"
        validate_document({"objects":{},"designPages":[page],"sectionOrder":[f"page:{page['id']}"]})
        return page

    def create_page_template(self):
        user=self.require_user()
        if not user:return
        data=self.body();name=str(data.get("name","")).strip()[:120];category=str(data.get("category","General")).strip()[:40] or "General"
        if not name:raise ValueError("Page template name is required")
        page=self.validate_page_template(data.get("page",{}));item_id=str(uuid.uuid4());now=int(time.time()*1000);favorite=1 if data.get("favorite") else 0
        with connect() as db:db.execute("INSERT INTO user_page_templates VALUES(?,?,?,?,?,?,?,?)",(item_id,user["id"],name,category,json.dumps(page),favorite,now,now))
        self.json(201,{"id":item_id,"name":name,"category":category,"page":page,"favorite":bool(favorite),"createdAt":now,"updatedAt":now})

    def update_page_template(self, template_id):
        user=self.require_user()
        if not user:return
        data=self.body();now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT * FROM user_page_templates WHERE id=? AND owner_id=?",(template_id,user["id"])).fetchone()
            if not row:return self.json(404,{"error":"Page template not found"})
            name=str(data.get("name",row["name"])).strip()[:120] or row["name"];category=str(data.get("category",row["category"])).strip()[:40] or "General";favorite=1 if data.get("favorite",bool(row["favorite"])) else 0;page_json=row["page_json"]
            if "page" in data:page_json=json.dumps(self.validate_page_template(data["page"]))
            db.execute("UPDATE user_page_templates SET name=?,category=?,page_json=?,favorite=?,updated_at=? WHERE id=? AND owner_id=?",(name,category,page_json,favorite,now,template_id,user["id"]))
            row=db.execute("SELECT * FROM user_page_templates WHERE id=?",(template_id,)).fetchone()
        self.json(200,{"id":row["id"],"name":row["name"],"category":row["category"],"page":json.loads(row["page_json"]),"favorite":bool(row["favorite"]),"createdAt":row["created_at"],"updatedAt":row["updated_at"]})

    def delete_page_template(self, template_id):
        user=self.require_user()
        if not user:return
        with connect() as db:changed=db.execute("DELETE FROM user_page_templates WHERE id=? AND owner_id=?",(template_id,user["id"])).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def validate_component_payload(self, kind, payload):
        if kind=="block":
            if not isinstance(payload,dict):raise ValueError("Content block must be an object")
            validate_document({"objects":{},"customBlocks":[payload]});return payload
        if kind=="group":
            if not isinstance(payload,dict) or not isinstance(payload.get("items",[]),list) or len(payload.get("items",[]))>100:raise ValueError("Invalid reusable element group")
            objects={}
            for index,item in enumerate(payload.get("items",[])):
                if not isinstance(item,dict) or not isinstance(item.get("data"),dict) or not isinstance(item.get("rel"),dict):raise ValueError("Invalid reusable group item")
                rel=item["rel"]
                for key in ("left","top","width","height"):
                    try:value=float(rel.get(key,0))
                    except (TypeError,ValueError):raise ValueError("Invalid reusable group position")
                    if not -1 <= value <= 2:raise ValueError("Invalid reusable group position")
                objects[f"component-{index}"]=item["data"]
            validate_document({"objects":objects});return payload
        raise ValueError("Unsupported component kind")

    def list_components(self):
        user=self.require_user()
        if not user:return
        kind=parse_qs(urlparse(self.path).query).get("kind",[None])[0]
        if kind not in (None,"group","block"):raise ValueError("Unsupported component kind")
        with connect() as db:
            if kind:rows=db.execute("SELECT * FROM user_components WHERE owner_id=? AND kind=? ORDER BY favorite DESC,updated_at DESC LIMIT 300",(user["id"],kind)).fetchall()
            else:rows=db.execute("SELECT * FROM user_components WHERE owner_id=? ORDER BY favorite DESC,updated_at DESC LIMIT 500",(user["id"],)).fetchall()
        self.json(200,[{"id":r["id"],"kind":r["kind"],"name":r["name"],"category":r["category"],"payload":json.loads(r["payload_json"]),"favorite":bool(r["favorite"]),"createdAt":r["created_at"],"updatedAt":r["updated_at"]} for r in rows])

    def create_component(self):
        user=self.require_user()
        if not user:return
        data=self.body();kind=str(data.get("kind",""));name=str(data.get("name","")).strip()[:120];category=str(data.get("category","General")).strip()[:40] or "General"
        if not name:raise ValueError("Component name is required")
        payload=self.validate_component_payload(kind,data.get("payload",{}));item_id=str(uuid.uuid4());now=int(time.time()*1000);favorite=1 if data.get("favorite") else 0
        with connect() as db:db.execute("INSERT INTO user_components VALUES(?,?,?,?,?,?,?,?,?)",(item_id,user["id"],kind,name,category,json.dumps(payload),favorite,now,now))
        self.json(201,{"id":item_id,"kind":kind,"name":name,"category":category,"payload":payload,"favorite":bool(favorite),"createdAt":now,"updatedAt":now})

    def update_component(self, component_id):
        user=self.require_user()
        if not user:return
        data=self.body();now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT * FROM user_components WHERE id=? AND owner_id=?",(component_id,user["id"])).fetchone()
            if not row:return self.json(404,{"error":"Reusable component not found"})
            name=str(data.get("name",row["name"])).strip()[:120] or row["name"];category=str(data.get("category",row["category"])).strip()[:40] or "General";favorite=1 if data.get("favorite",bool(row["favorite"])) else 0;payload_json=row["payload_json"]
            if "payload" in data:payload_json=json.dumps(self.validate_component_payload(row["kind"],data["payload"]))
            db.execute("UPDATE user_components SET name=?,category=?,payload_json=?,favorite=?,updated_at=? WHERE id=? AND owner_id=?",(name,category,payload_json,favorite,now,component_id,user["id"]))
            row=db.execute("SELECT * FROM user_components WHERE id=?",(component_id,)).fetchone()
        self.json(200,{"id":row["id"],"kind":row["kind"],"name":row["name"],"category":row["category"],"payload":json.loads(row["payload_json"]),"favorite":bool(row["favorite"]),"createdAt":row["created_at"],"updatedAt":row["updated_at"]})

    def delete_component(self, component_id):
        user=self.require_user()
        if not user:return
        with connect() as db:changed=db.execute("DELETE FROM user_components WHERE id=? AND owner_id=?",(component_id,user["id"])).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def studio_resource_owner(self, db, user, invitation_id=""):
        invitation_id=str(invitation_id or "").strip()
        if not invitation_id:return user["id"],True
        row=db.execute("SELECT owner_id FROM invitations WHERE id=? AND deleted_at IS NULL",(invitation_id,)).fetchone()
        if not row or not self.can_read_invitation(db,invitation_id,user["id"]):return None,False
        return row["owner_id"],row["owner_id"]==user["id"]

    def normalize_studio_resource(self, data, existing=None):
        if not isinstance(data,dict):raise ValueError("Invalid studio resource")
        kind=str(data.get("kind",existing["kind"] if existing else "")).strip().lower()
        if kind not in {"brand","template-family","component"}:raise ValueError("Unsupported studio resource kind")
        name=str(data.get("name",existing["name"] if existing else "")).strip()[:120]
        if not name:raise ValueError("Studio resource name is required")
        category=str(data.get("category",existing["category"] if existing else "General")).strip()[:60] or "General"
        status=str(data.get("status",existing["status"] if existing else "draft")).strip().lower()
        if status not in {"draft","approved","deprecated"}:raise ValueError("Invalid studio resource status")
        if "payload" in data:payload=data.get("payload")
        elif existing:
            try:payload=json.loads(existing["payload_json"] or "{}")
            except Exception:payload={}
        else:payload={}
        if not isinstance(payload,dict):raise ValueError("Studio resource payload must be an object")
        raw=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
        if len(raw.encode())>1_500_000:raise ValueError("Studio resource payload is too large")
        governance=data.get("governance") if "governance" in data else None
        if governance is None and existing:
            try:governance=json.loads(existing["governance_json"] or "{}")
            except Exception:governance={}
        if not isinstance(governance,dict):governance={}
        allowed=[]
        for value in governance.get("allowedOverrides",[]):
            value=str(value).strip()
            if value in {"content","media","colors","typography","layout","visibility"} and value not in allowed:allowed.append(value)
        normalized_governance={"locked":bool(governance.get("locked",False)),"allowedOverrides":allowed,"notes":str(governance.get("notes","")).strip()[:500]}
        return {"kind":kind,"name":name,"category":category,"status":status,"payload":payload,"governance":normalized_governance}

    def studio_resource_json(self, row, can_manage=False):
        try:payload=json.loads(row["payload_json"] or "{}")
        except Exception:payload={}
        try:governance=json.loads(row["governance_json"] or "{}")
        except Exception:governance={}
        return {"id":row["id"],"ownerId":row["owner_id"],"kind":row["kind"],"name":row["name"],"category":row["category"],"payload":payload,"governance":governance,"status":row["status"],"version":int(row["version"] or 1),"createdAt":row["created_at"],"updatedAt":row["updated_at"],"canManage":bool(can_manage)}

    def list_studio_resources(self):
        user=self.require_user()
        if not user:return
        query=parse_qs(urlparse(self.path).query);invitation_id=(query.get("invitationId") or [""])[0];kind=(query.get("kind") or [""])[0].strip().lower()
        if kind and kind not in {"brand","template-family","component"}:raise ValueError("Invalid studio resource kind")
        with connect() as db:
            owner_id,can_manage=self.studio_resource_owner(db,user,invitation_id)
            if not owner_id:return self.json(404,{"error":"Invitation not found"})
            if kind:rows=db.execute("SELECT * FROM studio_resources WHERE owner_id=? AND kind=? ORDER BY status='approved' DESC,updated_at DESC LIMIT 300",(owner_id,kind)).fetchall()
            else:rows=db.execute("SELECT * FROM studio_resources WHERE owner_id=? ORDER BY kind,status='approved' DESC,updated_at DESC LIMIT 500",(owner_id,)).fetchall()
        self.json(200,{"resources":[self.studio_resource_json(row,can_manage) for row in rows],"ownerId":owner_id,"canManage":can_manage})

    def create_studio_resource(self):
        user=self.require_user()
        if not user:return
        data=self.body(1_600_000);item=self.normalize_studio_resource(data);now=int(time.time()*1000);item_id=str(uuid.uuid4())
        with connect() as db:db.execute("INSERT INTO studio_resources(id,owner_id,kind,name,category,payload_json,governance_json,status,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)",(item_id,user["id"],item["kind"],item["name"],item["category"],json.dumps(item["payload"],ensure_ascii=False),json.dumps(item["governance"],ensure_ascii=False),item["status"],now,now));row=db.execute("SELECT * FROM studio_resources WHERE id=?",(item_id,)).fetchone()
        self.audit("studio.resource_created","studio_resource",item_id,{"kind":item["kind"],"status":item["status"]})
        self.json(201,self.studio_resource_json(row,True))

    def update_studio_resource(self, resource_id):
        user=self.require_user()
        if not user:return
        data=self.body(1_600_000);now=int(time.time()*1000)
        with connect() as db:
            existing=db.execute("SELECT * FROM studio_resources WHERE id=? AND owner_id=?",(resource_id,user["id"])).fetchone()
            if not existing:return self.json(404,{"error":"Studio resource not found"})
            item=self.normalize_studio_resource(data,existing);version=int(existing["version"] or 1)+(1 if "payload" in data else 0)
            db.execute("UPDATE studio_resources SET kind=?,name=?,category=?,payload_json=?,governance_json=?,status=?,version=?,updated_at=? WHERE id=? AND owner_id=?",(item["kind"],item["name"],item["category"],json.dumps(item["payload"],ensure_ascii=False),json.dumps(item["governance"],ensure_ascii=False),item["status"],version,now,resource_id,user["id"]));row=db.execute("SELECT * FROM studio_resources WHERE id=?",(resource_id,)).fetchone()
        self.audit("studio.resource_updated","studio_resource",resource_id,{"kind":item["kind"],"status":item["status"],"version":version})
        self.json(200,self.studio_resource_json(row,True))

    def delete_studio_resource(self, resource_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            active=db.execute("SELECT id,name,manifest_json FROM studio_releases WHERE owner_id=? AND status='active'",(user["id"],)).fetchall()
            for release in active:
                try:manifest=json.loads(release["manifest_json"] or "[]")
                except Exception:manifest=[]
                if any(isinstance(item,dict) and str(item.get("id",""))==resource_id for item in manifest):return self.json(409,{"error":f"This resource is included in active release {release['name']}. Retire or replace that release first.","code":"studio_resource_in_active_release"})
            changed=db.execute("DELETE FROM studio_resources WHERE id=? AND owner_id=?",(resource_id,user["id"])).rowcount
        if changed:self.audit("studio.resource_deleted","studio_resource",resource_id)
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def normalize_studio_release(self, data, existing=None):
        if not isinstance(data,dict):raise ValueError("Invalid studio release")
        name=str(data.get("name",existing["name"] if existing else "")).strip()[:120]
        if not name:raise ValueError("Studio release name is required")
        notes=str(data.get("notes",existing["notes"] if existing else "")).strip()[:1000]
        if "manifest" in data:manifest=data.get("manifest")
        elif existing:
            try:manifest=json.loads(existing["manifest_json"] or "[]")
            except Exception:manifest=[]
        else:manifest=[]
        if not isinstance(manifest,list):raise ValueError("Studio release manifest must be a list")
        normalized=[];seen=set()
        for item in manifest[:200]:
            if not isinstance(item,dict):continue
            resource_id=str(item.get("id","")).strip()[:100]
            kind=str(item.get("kind","")).strip().lower()
            if not resource_id or resource_id in seen or kind not in {"brand","template-family","component"}:continue
            seen.add(resource_id);normalized.append({"id":resource_id,"kind":kind,"name":str(item.get("name","")).strip()[:120],"version":max(1,int(item.get("version") or 1))})
        raw=json.dumps(normalized,ensure_ascii=False,separators=(",",":"))
        if len(raw.encode())>250_000:raise ValueError("Studio release manifest is too large")
        return {"name":name,"notes":notes,"manifest":normalized}

    def studio_release_json(self,row,can_manage=False):
        try:manifest=json.loads(row["manifest_json"] or "[]")
        except Exception:manifest=[]
        return {"id":row["id"],"ownerId":row["owner_id"],"name":row["name"],"notes":row["notes"],"status":row["status"],"manifest":manifest,"version":int(row["version"] or 1),"createdAt":row["created_at"],"updatedAt":row["updated_at"],"activatedAt":row["activated_at"],"canManage":bool(can_manage)}

    def validate_studio_release_manifest(self,db,owner_id,manifest):
        issues=[]
        if not manifest:issues.append({"code":"release_empty","message":"Add at least one approved studio resource."})
        for item in manifest:
            row=db.execute("SELECT id,kind,name,status,version FROM studio_resources WHERE id=? AND owner_id=?",(item["id"],owner_id)).fetchone()
            if not row:issues.append({"code":"release_resource_missing","message":f"Resource {item.get('name') or item['id']} is unavailable."})
            elif row["status"]!="approved":issues.append({"code":"release_resource_unapproved","message":f"{row['name']} is not approved."})
            elif str(row["kind"])!=str(item["kind"]):issues.append({"code":"release_resource_kind_changed","message":f"{row['name']} changed resource type."})
            elif int(row["version"] or 1)!=int(item["version"] or 1):issues.append({"code":"release_resource_outdated","message":f"{row['name']} is now version {row['version']}."})
        return issues

    def list_studio_releases(self):
        user=self.require_user()
        if not user:return
        query=parse_qs(urlparse(self.path).query);invitation_id=(query.get("invitationId") or [""])[0]
        with connect() as db:
            owner_id,can_manage=self.studio_resource_owner(db,user,invitation_id)
            if not owner_id:return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT * FROM studio_releases WHERE owner_id=? ORDER BY status='active' DESC,updated_at DESC LIMIT 100",(owner_id,)).fetchall()
        self.json(200,{"releases":[self.studio_release_json(row,can_manage) for row in rows],"ownerId":owner_id,"canManage":can_manage})

    def create_studio_release(self):
        user=self.require_user()
        if not user:return
        item=self.normalize_studio_release(self.body(300_000));now=int(time.time()*1000);release_id=str(uuid.uuid4())
        with connect() as db:
            for ref in item["manifest"]:
                if not db.execute("SELECT 1 FROM studio_resources WHERE id=? AND owner_id=?",(ref["id"],user["id"])).fetchone():raise ValueError("Studio release contains a resource from another studio")
            db.execute("INSERT INTO studio_releases(id,owner_id,name,notes,status,manifest_json,version,created_at,updated_at) VALUES(?,?,?,?, 'draft', ?,1,?,?)",(release_id,user["id"],item["name"],item["notes"],json.dumps(item["manifest"],ensure_ascii=False),now,now))
            row=db.execute("SELECT * FROM studio_releases WHERE id=?",(release_id,)).fetchone()
        self.audit("studio.release_created","studio_release",release_id,{"resources":len(item["manifest"])})
        self.json(201,self.studio_release_json(row,True))

    def update_studio_release(self,release_id):
        user=self.require_user()
        if not user:return
        data=self.body(300_000);now=int(time.time()*1000)
        with connect() as db:
            existing=db.execute("SELECT * FROM studio_releases WHERE id=? AND owner_id=?",(release_id,user["id"])).fetchone()
            if not existing:return self.json(404,{"error":"Studio release not found"})
            if existing["status"] in {"active","retired"} and "manifest" in data:return self.json(409,{"error":"Activated releases are immutable. Clone this release to create a new editable draft.","code":"activated_release_immutable"})
            item=self.normalize_studio_release(data,existing);version=int(existing["version"] or 1)+(1 if "manifest" in data else 0)
            db.execute("UPDATE studio_releases SET name=?,notes=?,manifest_json=?,version=?,updated_at=? WHERE id=? AND owner_id=?",(item["name"],item["notes"],json.dumps(item["manifest"],ensure_ascii=False),version,now,release_id,user["id"]))
            row=db.execute("SELECT * FROM studio_releases WHERE id=?",(release_id,)).fetchone()
        self.audit("studio.release_updated","studio_release",release_id,{"version":version})
        self.json(200,self.studio_release_json(row,True))

    def clone_studio_release(self,release_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);now=int(time.time()*1000);new_id=str(uuid.uuid4())
        with connect() as db:
            source=db.execute("SELECT * FROM studio_releases WHERE id=? AND owner_id=?",(release_id,user["id"])).fetchone()
            if not source:return self.json(404,{"error":"Studio release not found"})
            name=str(data.get("name") or f"{source['name']} — next").strip()[:120]
            notes=str(data.get("notes") or source["notes"] or "").strip()[:1000]
            db.execute("INSERT INTO studio_releases(id,owner_id,name,notes,status,manifest_json,version,created_at,updated_at) VALUES(?,?,?,?, 'draft', ?,1,?,?)",(new_id,user["id"],name,notes,source["manifest_json"],now,now))
            row=db.execute("SELECT * FROM studio_releases WHERE id=?",(new_id,)).fetchone()
        self.audit("studio.release_cloned","studio_release",new_id,{"sourceReleaseId":release_id})
        self.json(201,self.studio_release_json(row,True))

    def activate_studio_release(self,release_id):
        user=self.require_user()
        if not user:return
        now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT * FROM studio_releases WHERE id=? AND owner_id=?",(release_id,user["id"])).fetchone()
            if not row:return self.json(404,{"error":"Studio release not found"})
            try:manifest=json.loads(row["manifest_json"] or "[]")
            except Exception:manifest=[]
            issues=self.validate_studio_release_manifest(db,user["id"],manifest)
            if issues:return self.json(409,{"error":"The studio release is not ready for activation.","code":"studio_release_invalid","issues":issues})
            db.execute("UPDATE studio_releases SET status='retired',updated_at=? WHERE owner_id=? AND status='active' AND id<>?",(now,user["id"],release_id))
            db.execute("UPDATE studio_releases SET status='active',activated_at=?,updated_at=? WHERE id=? AND owner_id=?",(now,now,release_id,user["id"]))
            active=db.execute("SELECT * FROM studio_releases WHERE id=?",(release_id,)).fetchone()
        self.audit("studio.release_activated","studio_release",release_id,{"version":active["version"],"resources":len(manifest)})
        self.json(200,self.studio_release_json(active,True))

    def delete_studio_release(self,release_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            row=db.execute("SELECT status FROM studio_releases WHERE id=? AND owner_id=?",(release_id,user["id"])).fetchone()
            if not row:return self.json(404,{"deleted":False})
            if row["status"]=="active":return self.json(409,{"error":"Retire this release by activating another release before deleting it.","code":"active_release_delete_blocked"})
            pins=db.execute("SELECT COUNT(*) count FROM invitation_studio_release_pins WHERE release_id=?",(release_id,)).fetchone()
            if int(pins["count"] or 0)>0:return self.json(409,{"error":"This release is still pinned to invitations.","code":"release_still_pinned"})
            changed=db.execute("DELETE FROM studio_releases WHERE id=? AND owner_id=?",(release_id,user["id"])).rowcount
        if changed:self.audit("studio.release_deleted","studio_release",release_id)
        self.json(200,{"deleted":bool(changed)})

    def get_invitation_studio_release(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=db.execute("SELECT owner_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
            pin=db.execute("SELECT * FROM invitation_studio_release_pins WHERE invitation_id=?",(invite_id,)).fetchone()
            release=db.execute("SELECT * FROM studio_releases WHERE id=?",(pin["release_id"],)).fetchone() if pin else None
            active=db.execute("SELECT * FROM studio_releases WHERE owner_id=? AND status='active' ORDER BY activated_at DESC LIMIT 1",(owner["owner_id"],)).fetchone() if owner else None
            can_manage=self.can_manage_invitation(db,invite_id,user["id"])
        self.json(200,{"pin":dict(pin) if pin else None,"release":self.studio_release_json(release,False) if release else None,"activeRelease":self.studio_release_json(active,False) if active else None,"canManage":can_manage})

    def pin_invitation_studio_release(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);release_id=str(data.get("releaseId","")).strip();now=int(time.time()*1000)
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Invitation management permission required"})
            invitation=db.execute("SELECT owner_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
            if not invitation:return self.json(404,{"error":"Invitation not found"})
            if not release_id:
                db.execute("DELETE FROM invitation_studio_release_pins WHERE invitation_id=?",(invite_id,));self.audit("studio.release_unpinned","invitation",invite_id);return self.json(200,{"pin":None})
            release=db.execute("SELECT * FROM studio_releases WHERE id=? AND owner_id=?",(release_id,invitation["owner_id"])).fetchone()
            if not release:return self.json(404,{"error":"Studio release not found"})
            if release["status"]!="active":return self.json(409,{"error":"Only the active studio release can be pinned.","code":"release_not_active"})
            existing=db.execute("SELECT invitation_id FROM invitation_studio_release_pins WHERE invitation_id=?",(invite_id,)).fetchone()
            if existing:db.execute("UPDATE invitation_studio_release_pins SET owner_id=?,release_id=?,release_version=?,pinned_by=?,updated_at=? WHERE invitation_id=?",(invitation["owner_id"],release_id,int(release["version"] or 1),user["id"],now,invite_id))
            else:db.execute("INSERT INTO invitation_studio_release_pins(invitation_id,owner_id,release_id,release_version,pinned_by,pinned_at,updated_at) VALUES(?,?,?,?,?,?,?)",(invite_id,invitation["owner_id"],release_id,int(release["version"] or 1),user["id"],now,now))
            pin=db.execute("SELECT * FROM invitation_studio_release_pins WHERE invitation_id=?",(invite_id,)).fetchone()
        self.audit("studio.release_pinned","invitation",invite_id,{"releaseId":release_id,"releaseVersion":release["version"]})
        self.json(200,{"pin":dict(pin),"release":self.studio_release_json(release,False)})

    def studio_release_adoption(self):
        user=self.require_user()
        if not user:return
        query=parse_qs(urlparse(self.path).query);invitation_id=(query.get("invitationId") or [""])[0]
        with connect() as db:
            owner_id,can_manage=self.studio_resource_owner(db,user,invitation_id)
            if not owner_id:return self.json(404,{"error":"Invitation not found"})
            if not can_manage:return self.json(403,{"error":"Only the studio owner can view organization-wide adoption"})
            active=db.execute("SELECT * FROM studio_releases WHERE owner_id=? AND status='active' ORDER BY activated_at DESC LIMIT 1",(owner_id,)).fetchone()
            try:active_manifest=json.loads(active["manifest_json"] or "[]") if active else []
            except Exception:active_manifest=[]
            release_issues=self.validate_studio_release_manifest(db,owner_id,active_manifest) if active else []
            rows=db.execute("SELECT i.id,i.slug,i.draft_json,i.updated_at,i.is_published,p.release_id,p.release_version,p.updated_at pin_updated FROM invitations i LEFT JOIN invitation_studio_release_pins p ON p.invitation_id=i.id WHERE i.owner_id=? AND i.deleted_at IS NULL ORDER BY i.updated_at DESC LIMIT 500",(owner_id,)).fetchall()
        invitations=[];counts={"current":0,"outdated":0,"unpinned":0}
        for row in rows:
            try:doc=json.loads(row["draft_json"] or "{}")
            except Exception:doc={}
            if not row["release_id"]:state="unpinned"
            elif not active or release_issues or row["release_id"]!=active["id"] or int(row["release_version"] or 0)!=int(active["version"] or 1):state="outdated"
            else:state="current"
            counts[state]+=1
            invitations.append({"id":row["id"],"slug":row["slug"],"title":str((doc.get("fields") or {}).get("names") or (doc.get("fields") or {}).get("title") or row["slug"])[:160],"published":bool(row["is_published"]),"updatedAt":row["updated_at"],"releaseId":row["release_id"],"releaseVersion":row["release_version"],"state":state})
        self.json(200,{"activeRelease":self.studio_release_json(active,True) if active else None,"releaseIssues":release_issues,"counts":counts,"invitations":invitations})

    def bulk_pin_studio_release(self,release_id):
        user=self.require_user()
        if not user:return
        data=self.body(200_000);scope=str(data.get("scope") or "selected").strip().lower();requested=data.get("invitationIds") or []
        if scope not in {"selected","unpinned","outdated","noncurrent"}:raise ValueError("Unsupported bulk-pin scope")
        if not isinstance(requested,list) or len(requested)>500:raise ValueError("Bulk pin supports at most 500 invitations")
        requested_ids={str(value).strip() for value in requested if str(value).strip()}
        now=int(time.time()*1000);job_id=str(uuid.uuid4())
        updated=[];manual=[];skipped=[]
        with connect() as db:
            release=db.execute("SELECT * FROM studio_releases WHERE id=? AND owner_id=?",(release_id,user["id"])).fetchone()
            if not release:return self.json(404,{"error":"Studio release not found"})
            if release["status"]!="active":return self.json(409,{"error":"Only the active studio release can be applied in bulk.","code":"release_not_active"})
            try:manifest=json.loads(release["manifest_json"] or "[]")
            except Exception:manifest=[]
            release_issues=self.validate_studio_release_manifest(db,user["id"],manifest)
            if release_issues:return self.json(409,{"error":"The active studio release contains changed or unavailable resources.","code":"studio_release_invalid","issues":release_issues})
            manifest_map={str(item.get("id","")):(int(item.get("version") or 1),str(item.get("kind") or "")) for item in manifest if isinstance(item,dict) and item.get("id")}
            rows=db.execute("SELECT i.id,i.slug,i.draft_json,p.release_id,p.release_version FROM invitations i LEFT JOIN invitation_studio_release_pins p ON p.invitation_id=i.id WHERE i.owner_id=? AND i.deleted_at IS NULL ORDER BY i.updated_at DESC LIMIT 500",(user["id"],)).fetchall()
            targets=[]
            for row in rows:
                is_current=row["release_id"]==release_id and int(row["release_version"] or 0)==int(release["version"] or 1)
                include=(scope=="selected" and row["id"] in requested_ids) or (scope=="unpinned" and not row["release_id"]) or (scope=="outdated" and bool(row["release_id"]) and not is_current) or (scope=="noncurrent" and not is_current)
                if include:targets.append(row)
            for row in targets:
                try:document=json.loads(row["draft_json"] or "{}")
                except Exception:document={}
                incompatible=[]
                for ref in studio_document_resource_references(document):
                    expected=manifest_map.get(ref["id"])
                    if not expected:incompatible.append({"code":"resource_outside_release","resourceId":ref["id"]})
                    elif ref["version"] and ref["version"]!=expected[0]:incompatible.append({"code":"resource_version_mismatch","resourceId":ref["id"],"currentVersion":ref["version"],"releaseVersion":expected[0]})
                if incompatible:
                    manual.append({"id":row["id"],"slug":row["slug"],"issues":incompatible});continue
                existing=db.execute("SELECT invitation_id FROM invitation_studio_release_pins WHERE invitation_id=?",(row["id"],)).fetchone()
                if existing:db.execute("UPDATE invitation_studio_release_pins SET owner_id=?,release_id=?,release_version=?,pinned_by=?,updated_at=? WHERE invitation_id=?",(user["id"],release_id,int(release["version"] or 1),user["id"],now,row["id"]))
                else:db.execute("INSERT INTO invitation_studio_release_pins(invitation_id,owner_id,release_id,release_version,pinned_by,pinned_at,updated_at) VALUES(?,?,?,?,?,?,?)",(row["id"],user["id"],release_id,int(release["version"] or 1),user["id"],now,now))
                updated.append(row["id"])
            if scope=="selected":skipped=sorted(requested_ids-{row["id"] for row in targets})
            selection={"scope":scope,"invitationIds":sorted(requested_ids)};result={"updated":updated,"manual":manual,"skipped":skipped,"releaseId":release_id,"releaseVersion":int(release["version"] or 1)}
            db.execute("INSERT INTO studio_bulk_jobs(id,owner_id,kind,status,selection_json,result_json,created_by,created_at,completed_at) VALUES(?,?, 'release-pin','completed',?,?,?,?,?)",(job_id,user["id"],json.dumps(selection),json.dumps(result),user["id"],now,now))
        self.audit("studio.release_bulk_pinned","studio_release",release_id,{"updated":len(updated),"manual":len(manual),"scope":scope,"jobId":job_id})
        self.json(200,{"jobId":job_id,"updated":updated,"manual":manual,"skipped":skipped,"count":len(updated)})

    def list_studio_bulk_jobs(self):
        user=self.require_user()
        if not user:return
        with connect() as db:rows=db.execute("SELECT * FROM studio_bulk_jobs WHERE owner_id=? ORDER BY created_at DESC LIMIT 50",(user["id"],)).fetchall()
        items=[]
        for row in rows:
            try:selection=json.loads(row["selection_json"] or "{}")
            except Exception:selection={}
            try:result=json.loads(row["result_json"] or "{}")
            except Exception:result={}
            items.append({"id":row["id"],"kind":row["kind"],"status":row["status"],"selection":selection,"result":result,"createdBy":row["created_by"],"createdAt":row["created_at"],"completedAt":row["completed_at"]})
        self.json(200,{"jobs":items})

    def studio_operations_audit(self):
        user=self.require_user()
        if not user:return
        query=parse_qs(urlparse(self.path).query);limit=max(1,min(300,int((query.get("limit") or [150])[0])));term=str((query.get("q") or [""])[0]).strip().lower()
        with connect() as db:
            rows=db.execute("""
                SELECT a.id,a.user_id,a.action,a.target_type,a.target_id,a.metadata_json,a.ip_address,a.previous_hash,a.event_hash,a.created_at,u.email actor_email
                FROM audit_events a LEFT JOIN users u ON u.id=a.user_id
                WHERE a.user_id=?
                   OR (a.target_type='invitation' AND a.target_id IN (SELECT id FROM invitations WHERE owner_id=?))
                   OR (a.target_type='studio_release' AND a.target_id IN (SELECT id FROM studio_releases WHERE owner_id=?))
                   OR (a.target_type='studio_resource' AND a.target_id IN (SELECT id FROM studio_resources WHERE owner_id=?))
                ORDER BY a.created_at DESC LIMIT ?
            """,(user["id"],user["id"],user["id"],user["id"],limit)).fetchall()
        events=[]
        for row in rows:
            try:metadata=json.loads(row["metadata_json"] or "{}")
            except Exception:metadata={}
            raw_meta=row["metadata_json"] or "{}";payload=f"{row['id']}|{row['user_id'] or ''}|{row['action']}|{row['target_type']}|{row['target_id']}|{raw_meta}|{row['ip_address']}|{row['previous_hash']}|{row['created_at']}";valid_hash=hmac.compare_digest(hashlib.sha256(payload.encode()).hexdigest(),str(row["event_hash"] or ""))
            actor_ip=str(row["ip_address"] or "")
            if row["user_id"] and row["user_id"]!=user["id"]:
                if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}",actor_ip):actor_ip=actor_ip.rsplit('.',1)[0]+'.0'
                elif ':' in actor_ip:actor_ip=':'.join(actor_ip.split(':')[:4])+':…'
            item={"id":row["id"],"actorId":row["user_id"] or "","actorEmail":row["actor_email"] or "Deleted account","action":row["action"],"targetType":row["target_type"],"targetId":row["target_id"],"metadata":metadata,"ipAddress":actor_ip,"createdAt":row["created_at"],"hash":row["event_hash"],"previousHash":row["previous_hash"],"validHash":valid_hash}
            if term and term not in json.dumps(item,ensure_ascii=False).lower():continue
            events.append(item)
        self.json(200,{"events":events,"immutable":True,"hashChained":True})

    def get_studio_backup_policy(self):
        user=self.require_user()
        if not user:return
        with connect() as db:row=db.execute("SELECT * FROM studio_backup_policies WHERE owner_id=?",(user["id"],)).fetchone()
        policy=dict(row) if row else {"owner_id":user["id"],"enabled":0,"interval_hours":24,"retention_count":7,"include_media":1,"updated_at":0,"last_run_at":None,"next_run_at":None}
        self.json(200,{"policy":{"enabled":bool(policy["enabled"]),"intervalHours":policy["interval_hours"],"retentionCount":policy["retention_count"],"includeMedia":bool(policy["include_media"]),"updatedAt":policy["updated_at"],"lastRunAt":policy["last_run_at"],"nextRunAt":policy["next_run_at"]}})

    def update_studio_backup_policy(self):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);enabled=bool(data.get("enabled",False));interval=max(1,min(720,int(data.get("intervalHours",24))));retention=max(1,min(30,int(data.get("retentionCount",7))));include_media=bool(data.get("includeMedia",True));now=int(time.time()*1000);next_run=now+interval*3600000 if enabled else None
        with connect() as db:
            existing=db.execute("SELECT owner_id,last_run_at FROM studio_backup_policies WHERE owner_id=?",(user["id"],)).fetchone()
            if existing:db.execute("UPDATE studio_backup_policies SET enabled=?,interval_hours=?,retention_count=?,include_media=?,updated_by=?,updated_at=?,next_run_at=? WHERE owner_id=?",(int(enabled),interval,retention,int(include_media),user["id"],now,next_run,user["id"]))
            else:db.execute("INSERT INTO studio_backup_policies(owner_id,enabled,interval_hours,retention_count,include_media,updated_by,updated_at,next_run_at) VALUES(?,?,?,?,?,?,?,?)",(user["id"],int(enabled),interval,retention,int(include_media),user["id"],now,next_run))
        prune_studio_backups(user["id"],retention);self.audit("studio.backup_policy_updated","user",user["id"],{"enabled":enabled,"intervalHours":interval,"retentionCount":retention,"includeMedia":include_media})
        self.json(200,{"policy":{"enabled":enabled,"intervalHours":interval,"retentionCount":retention,"includeMedia":include_media,"updatedAt":now,"nextRunAt":next_run}})

    def run_studio_backup_now(self):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);include_media=bool(data.get("includeMedia",True));result=run_studio_backup(user["id"],user["id"],"manual",include_media)
        if result["status"]=="busy":return self.json(409,{"error":result["error"],"code":"studio_backup_busy"})
        self.json(200 if result["status"]=="completed" else 500,result)

    def list_studio_backups(self):
        user=self.require_user()
        if not user:return
        with connect() as db:rows=db.execute("SELECT * FROM backup_runs WHERE owner_id=? ORDER BY created_at DESC LIMIT 50",(user["id"],)).fetchall()
        items=[]
        for row in rows:
            try:detail=json.loads(row["detail_json"] or "{}")
            except Exception:detail={}
            items.append({"id":row["id"],"kind":row["kind"],"status":row["status"],"detail":detail,"createdAt":row["created_at"],"completedAt":row["completed_at"],"sizeBytes":row["size_bytes"],"error":row["error_text"],"downloadUrl":f"/api/studio/backups/{row['id']}/download" if row["status"]=="completed" else ""})
        self.json(200,{"backups":items})

    def download_studio_backup(self,run_id):
        user=self.require_user()
        if not user:return
        with connect() as db:row=db.execute("SELECT archive_name FROM backup_runs WHERE id=? AND owner_id=? AND status='completed'",(run_id,user["id"])).fetchone()
        if not row:return self.json(404,{"error":"Backup not found"})
        name=Path(str(row["archive_name"] or "")).name;target=BACKUPS/name
        if not name or not target.is_file():return self.json(404,{"error":"Backup file is unavailable"})
        raw=target.read_bytes();self.send_response(200);self.send_header("Content-Type","application/zip");self.send_header("Content-Disposition",f'attachment; filename="{name}"');self.send_header("Cache-Control","private,no-store");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)

    def normalize_studio_policy(self, data):
        if not isinstance(data,dict):data={}
        return {"approvedOnly":bool(data.get("approvedOnly",False)),"lockBrandColors":bool(data.get("lockBrandColors",False)),"lockTypography":bool(data.get("lockTypography",False)),"requireAdaptiveTemplate":bool(data.get("requireAdaptiveTemplate",False)),"requirePrintPreflight":bool(data.get("requirePrintPreflight",False)),"requireStudioRelease":bool(data.get("requireStudioRelease",False)),"updatedByAdmin":bool(data.get("updatedByAdmin",False))}

    def get_studio_governance(self):
        user=self.require_user()
        if not user:return
        query=parse_qs(urlparse(self.path).query);invitation_id=(query.get("invitationId") or [""])[0]
        with connect() as db:
            owner_id,can_manage=self.studio_resource_owner(db,user,invitation_id)
            if not owner_id:return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT policy_json,updated_at FROM studio_governance WHERE owner_id=?",(owner_id,)).fetchone()
        try:policy=json.loads(row["policy_json"] or "{}") if row else {}
        except Exception:policy={}
        self.json(200,{"ownerId":owner_id,"canManage":can_manage,"policy":self.normalize_studio_policy(policy),"updatedAt":row["updated_at"] if row else 0})

    def update_studio_governance(self):
        user=self.require_user()
        if not user:return
        policy=self.normalize_studio_policy(self.body(50_000));now=int(time.time()*1000)
        with connect() as db:
            existing=db.execute("SELECT owner_id FROM studio_governance WHERE owner_id=?",(user["id"],)).fetchone()
            if existing:db.execute("UPDATE studio_governance SET policy_json=?,updated_at=? WHERE owner_id=?",(json.dumps(policy),now,user["id"]))
            else:db.execute("INSERT INTO studio_governance(owner_id,policy_json,updated_at) VALUES(?,?,?)",(user["id"],json.dumps(policy),now))
        self.audit("studio.governance_updated","user",user["id"],policy)
        self.json(200,{"ownerId":user["id"],"canManage":True,"policy":policy,"updatedAt":now})

    def get_account_assets(self):
        user=self.require_user()
        if not user:return
        accessible="i.owner_id=? OR EXISTS(SELECT 1 FROM invitation_collaborators c WHERE c.invitation_id=i.id AND c.user_id=?)"
        with connect() as db:
            rows=db.execute(f"""SELECT a.id,a.invitation_id,a.name,a.mime,a.path,a.size,a.created_at,a.folder,a.tags_json,a.favorite,a.sha256,a.width,a.height,a.dominant_color,i.slug
                               FROM assets a JOIN invitations i ON i.id=a.invitation_id
                               WHERE {accessible} ORDER BY a.favorite DESC,a.created_at DESC LIMIT 1000""",(user["id"],user["id"])).fetchall()
            draft_rows=db.execute(f"SELECT i.draft_json FROM invitations i WHERE {accessible}",(user["id"],user["id"])).fetchall()
            published_rows=db.execute(f"SELECT p.document_json FROM publications p JOIN invitations i ON i.id=p.invitation_id WHERE {accessible}",(user["id"],user["id"])).fetchall()
        searchable="\n".join(str(x["draft_json"] or "") for x in draft_rows)+"\n"+"\n".join(str(x["document_json"] or "") for x in published_rows)
        result=[]
        for r in rows:
            try: tags=json.loads(r["tags_json"] or "[]")
            except Exception: tags=[]
            url=asset_public_url(r['path']);usage_count=searchable.count(url)
            result.append({"id":r["id"],"invitationId":r["invitation_id"],"invitationSlug":r["slug"],"name":r["name"],"mime":r["mime"],"url":url,"size":r["size"],"createdAt":r["created_at"],"folder":r["folder"],"tags":tags,"favorite":bool(r["favorite"]),"sha256":r["sha256"],"width":r["width"],"height":r["height"],"dominantColor":r["dominant_color"],"responsiveBase":responsive_asset_url(r["path"]),"usageCount":usage_count})
        self.json(200,result)

    def get_material_folders(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,parent_id,name,relative_key,created_by,created_at,updated_at FROM material_folders WHERE invitation_id=? ORDER BY relative_key",(invite_id,)).fetchall()
        self.json(200,{"folders":[{"id":r["id"],"parentId":r["parent_id"],"name":r["name"],"folder":r["relative_key"],"createdBy":r["created_by"],"createdAt":r["created_at"],"updatedAt":r["updated_at"]} for r in rows]})

    def create_material_folder(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        data=self.body(20_000);folder_name=sanitize_material_folder(data.get("folder") or data.get("folderName") or "");parent_id=str(data.get("parentFolderId") or "").strip()[:120]
        if not folder_name:raise ValueError("Folder name is required")
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            folder=folder_name
            if parent_id:
                parent=db.execute("SELECT relative_key FROM material_folders WHERE id=? AND invitation_id=?",(parent_id,invite_id)).fetchone()
                if not parent:raise ValueError("Parent material folder was not found")
                folder=sanitize_material_folder(f"{parent['relative_key']}/{folder_name}")
            folder_id=ensure_material_folder_chain(db,invite_id,user["id"],folder)
            row=db.execute("SELECT id,parent_id,name,relative_key,created_at,updated_at FROM material_folders WHERE id=?",(folder_id,)).fetchone()
        self.json(201,{"folder":{"id":row["id"],"parentId":row["parent_id"],"name":row["name"],"folder":row["relative_key"],"createdAt":row["created_at"],"updatedAt":row["updated_at"]}})

    def find_material_duplicates(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,name,mime,size,sha256,folder FROM assets WHERE invitation_id=? AND COALESCE(sha256,'')<>'' ORDER BY sha256,created_at",(invite_id,)).fetchall()
        grouped={}
        for row in rows:grouped.setdefault(str(row["sha256"]),[]).append({"id":row["id"],"name":row["name"],"mime":row["mime"],"size":row["size"],"folder":row["folder"] or ""})
        groups=[{"sha256":digest,"count":len(items),"assets":items} for digest,items in grouped.items() if len(items)>1]
        self.json(200,{"groups":groups[:500]})

    def move_material(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);asset_id=str(data.get("assetId") or "").strip()[:120];folder_id=str(data.get("folderId") or "").strip()[:120]
        if not asset_id or not folder_id:raise ValueError("Material and target folder are required")
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            folder=db.execute("SELECT relative_key FROM material_folders WHERE id=? AND invitation_id=?",(folder_id,invite_id)).fetchone()
            if not folder:return self.json(404,{"error":"Material folder not found"})
            changed=db.execute("UPDATE assets SET folder=? WHERE id=? AND invitation_id=?",(folder["relative_key"],asset_id,invite_id)).rowcount
            row=db.execute("SELECT id,name,mime,size,folder,tags_json,favorite FROM assets WHERE id=? AND invitation_id=?",(asset_id,invite_id)).fetchone()
        if not changed or not row:return self.json(404,{"error":"Material not found"})
        try:tags=json.loads(row["tags_json"] or "[]")
        except Exception:tags=[]
        self.audit("material.moved","asset",asset_id,{"invitationId":invite_id,"folder":row["folder"]})
        self.json(200,{"asset":{"id":row["id"],"name":row["name"],"mime":row["mime"],"size":row["size"],"folder":row["folder"],"tags":tags,"favorite":bool(row["favorite"])}})

    def rename_material(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);asset_id=str(data.get("assetId") or "").strip()[:120];name=str(data.get("name") or "").strip()[:180]
        if not asset_id or not name:raise ValueError("Material and name are required")
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            changed=db.execute("UPDATE assets SET name=? WHERE id=? AND invitation_id=?",(name,asset_id,invite_id)).rowcount
            row=db.execute("SELECT id,name,mime,size,folder,tags_json,favorite FROM assets WHERE id=? AND invitation_id=?",(asset_id,invite_id)).fetchone()
        if not changed or not row:return self.json(404,{"error":"Material not found"})
        try:tags=json.loads(row["tags_json"] or "[]")
        except Exception:tags=[]
        self.audit("material.renamed","asset",asset_id,{"invitationId":invite_id})
        self.json(200,{"asset":{"id":row["id"],"name":row["name"],"mime":row["mime"],"size":row["size"],"folder":row["folder"],"tags":tags,"favorite":bool(row["favorite"])}})

    def classify_materials(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);asset_ids=data.get("assetIds") or [];category=str(data.get("category") or "").strip()[:60];extra=data.get("tags") or []
        if not isinstance(asset_ids,list) or not asset_ids or len(asset_ids)>100:raise ValueError("One to 100 material IDs are required")
        if not category:raise ValueError("Material category is required")
        if not isinstance(extra,list) or len(extra)>30:raise ValueError("Invalid material tags")
        tags=[category]+[str(x).strip()[:60] for x in extra if str(x).strip()];tags=list(dict.fromkeys(tags))[:30];updated=[]
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            for asset_id in [str(x)[:120] for x in asset_ids]:
                row=db.execute("SELECT tags_json FROM assets WHERE id=? AND invitation_id=?",(asset_id,invite_id)).fetchone()
                if not row:continue
                try:existing=json.loads(row["tags_json"] or "[]")
                except Exception:existing=[]
                merged=list(dict.fromkeys([str(x)[:60] for x in existing if str(x).strip()]+tags))[:30]
                db.execute("UPDATE assets SET tags_json=? WHERE id=? AND invitation_id=?",(json.dumps(merged,ensure_ascii=False),asset_id,invite_id));updated.append(asset_id)
        self.audit("materials.classified","invitation",invite_id,{"count":len(updated),"category":category})
        self.json(200,{"updatedIds":updated})

    def get_material_import_jobs(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT * FROM material_import_jobs WHERE invitation_id=? ORDER BY created_at DESC LIMIT 50",(invite_id,)).fetchall()
        jobs=[]
        for r in rows:
            try:failures=json.loads(r["failures_json"] or "[]")
            except Exception:failures=[]
            jobs.append({"id":r["id"],"sourceType":r["source_type"],"rootName":r["root_name"],"status":r["status"],"totalFiles":r["total_files"],"processedFiles":r["processed_files"],"failedFiles":r["failed_files"],"totalBytes":r["total_bytes"],"processedBytes":r["processed_bytes"],"failures":failures,"createdAt":r["created_at"],"updatedAt":r["updated_at"],"cancelledAt":r["cancelled_at"]})
        self.json(200,{"jobs":jobs})

    def start_material_import_job(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        data=self.body(500_000);files=data.get("files") or [];empty_dirs=data.get("emptyDirectories") or []
        if not isinstance(files,list) or len(files)>MATERIAL_IMPORT_MAX_ENTRIES:raise ValueError("Folder import contains too many files")
        if not isinstance(empty_dirs,list) or len(empty_dirs)>MATERIAL_IMPORT_MAX_ENTRIES:raise ValueError("Folder import contains too many folders")
        total_bytes=0
        for item in files:
            if not isinstance(item,dict):raise ValueError("Invalid folder import manifest")
            folder=sanitize_material_folder(item.get("folder") or "")
            size=max(0,int(item.get("size") or 0));total_bytes+=size
            if size<=0:raise ValueError("Folder import contains an empty file")
        if total_bytes>MATERIAL_IMPORT_MAX_UNCOMPRESSED_BYTES:raise ValueError("Folder import batch is too large")
        root=sanitize_material_folder(data.get("rootName") or "")
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        if not self.require_plan_capacity(owner,"storageBytes",total_bytes):return
        now=int(time.time()*1000);job_id=str(uuid.uuid4())
        with connect() as db:
            for folder in empty_dirs:
                key=sanitize_material_folder(folder)
                if key:ensure_material_folder_chain(db,invite_id,user["id"],key)
            if root:ensure_material_folder_chain(db,invite_id,user["id"],root)
            db.execute("INSERT INTO material_import_jobs(id,invitation_id,owner_id,source_type,root_name,status,total_files,total_bytes,created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?,?,?)",(job_id,invite_id,owner["id"],"directory",root,len(files),total_bytes,now,now))
        self.json(201,{"id":job_id,"status":"queued","rootName":root,"totalFiles":len(files),"totalBytes":total_bytes})

    def report_material_import_failure(self, invite_id, job_id):
        user=self.require_user()
        if not user:return
        data=self.body(20_000);failure={"name":str(data.get("name") or "")[:180],"folder":sanitize_material_folder(data.get("folder") or ""),"error":str(data.get("error") or "Upload failed")[:300]}
        processed=max(0,min(MATERIAL_IMPORT_MAX_UNCOMPRESSED_BYTES,int(data.get("size") or 0)))
        with connect() as db:
            row=db.execute("SELECT id,status FROM material_import_jobs WHERE id=? AND invitation_id=?",(job_id,invite_id)).fetchone()
            if not row or not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Import job not found"})
            if row["status"]=="cancelled":return self.json(409,{"error":"Import job was cancelled","code":"import_cancelled"})
        update_material_import_job(job_id,processed,False,failure)
        self.json(200,{"recorded":True,"failure":failure})

    def cancel_material_import_job(self, invite_id, job_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            row=db.execute("SELECT id,status FROM material_import_jobs WHERE id=? AND invitation_id=?",(job_id,invite_id)).fetchone()
            if not row or not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Import job not found"})
            if row["status"] in {"completed","cancelled"}:return self.json(200,{"cancelled":row["status"]=="cancelled","status":row["status"]})
            now=int(time.time()*1000);db.execute("UPDATE material_import_jobs SET status='cancelled',cancelled_at=?,updated_at=? WHERE id=?",(now,now,job_id))
        self.json(200,{"cancelled":True,"status":"cancelled"})

    def import_material_zip(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        if not self.rate_limit(f"zip-import:{user['id']}:{invite_id}",10,3600):return
        size=int(self.headers.get("Content-Length","0") or 0)
        if size<=0 or size>MATERIAL_IMPORT_MAX_ARCHIVE_BYTES:raise ValueError("ZIP archive is empty or exceeds the configured archive limit")
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        raw=self.rfile.read(size)
        if len(raw)!=size or not raw.startswith(b"PK"):raise ValueError("The uploaded file is not a valid ZIP archive")
        root=sanitize_material_folder(unquote(str(self.headers.get("X-Material-Root",""))))
        try:archive=zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:raise ValueError("The uploaded file is not a valid ZIP archive")
        infos=archive.infolist()
        if len(infos)>MATERIAL_IMPORT_MAX_ENTRIES:raise ValueError("ZIP archive contains too many entries")
        total_uncompressed=sum(max(0,int(i.file_size or 0)) for i in infos if not i.is_dir())
        if total_uncompressed>MATERIAL_IMPORT_MAX_UNCOMPRESSED_BYTES:raise ValueError("ZIP archive expands beyond the configured batch limit")
        # Full-archive traversal/symlink validation happens before any write.
        entries=[];empty_dirs=[]
        dangerous_ext={".exe",".dll",".msi",".bat",".cmd",".ps1",".sh",".com",".scr",".jar",".js",".vbs",".py",".php",".pl",".rb"}
        for info in infos:
            name=str(info.filename or "").replace("\\","/")
            clean=validate_material_zip_entry_path(name)
            unix_mode=(int(info.external_attr or 0)>>16)&0o170000
            if unix_mode==0o120000:raise ValueError("ZIP symbolic links are not allowed")
            if info.is_dir():
                if clean:empty_dirs.append(clean)
                continue
            entry_size=max(0,int(info.file_size or 0));compressed=max(1,int(info.compress_size or 0))
            if entry_size>MATERIAL_IMPORT_MAX_ENTRY_BYTES:raise ValueError("ZIP contains an entry larger than the configured per-file limit")
            if entry_size>1_000_000 and entry_size/compressed>MATERIAL_IMPORT_MAX_COMPRESSION_RATIO:
                raise ValueError("ZIP contains a suspiciously compressed entry")
            ext=Path(clean).suffix.lower()
            if ext in dangerous_ext:raise ValueError("ZIP contains an executable or script file, which is not allowed")
            mime=(mimetypes.guess_type(Path(clean).name)[0] or "application/octet-stream").lower()
            entries.append((info,clean,mime))
        # Avoid duplicating the archive root when the ZIP already contains that same top-level folder.
        inferred_root=root or sanitize_material_folder(Path(unquote(str(self.headers.get("X-File-Name","materials.zip")))).stem)
        top_parts={clean.split("/",1)[0] for _,clean,_ in entries if clean}
        if inferred_root and len(top_parts)==1 and next(iter(top_parts),"")==inferred_root:
            entries=[(info,clean.split("/",1)[1] if "/" in clean else Path(clean).name,mime) for info,clean,mime in entries]
            empty_dirs=[folder.split("/",1)[1] if folder.startswith(inferred_root+"/") else ("" if folder==inferred_root else folder) for folder in empty_dirs]
        # Capacity uses the worst case; physical checksum dedupe later avoids double charging.
        if not self.require_plan_capacity(owner,"storageBytes",total_uncompressed):return
        now=int(time.time()*1000);job_id=str(uuid.uuid4());root_name=inferred_root
        with connect() as db:
            if root_name:ensure_material_folder_chain(db,invite_id,user["id"],root_name)
            for folder in empty_dirs:
                key="/".join(x for x in (root_name,folder) if x)
                if key:ensure_material_folder_chain(db,invite_id,user["id"],key)
            db.execute("INSERT INTO material_import_jobs(id,invitation_id,owner_id,source_type,root_name,status,total_files,total_bytes,created_at,updated_at) VALUES(?,?,?,?,?,'running',?,?,?,?)",(job_id,invite_id,owner["id"],"zip",root_name,len(entries),total_uncompressed,now,now))
        failures=[];created=[]
        for info,clean,mime in entries:
            with connect() as db:
                job=db.execute("SELECT status FROM material_import_jobs WHERE id=?",(job_id,)).fetchone()
            if not job or job["status"]=="cancelled":break
            folder=sanitize_material_folder(str(Path(clean).parent).replace("\\","/")) if "/" in clean else ""
            folder="/".join(x for x in (root_name,folder) if x);name=Path(clean).name[:180] or "upload"
            try:
                if info.flag_bits & 0x1:raise ValueError("Encrypted ZIP entries are not supported")
                file_raw=archive.read(info)
                validate_material_request(mime,len(file_raw));validate_material_bytes(file_raw,mime)
                digest=hashlib.sha256(file_raw).hexdigest()
                with connect() as db:existing=db.execute("SELECT id FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime=? AND processing_state='ready' LIMIT 1",(owner["id"],digest,len(file_raw),mime)).fetchone()
                if not existing and not self.require_plan_capacity(owner,"storageBytes",len(file_raw)):
                    raise ValueError("Storage limit reached during ZIP import")
                aid=str(uuid.uuid4());stored=acquire_stored_object(owner["id"],aid,file_raw,mime,scan_name=name);payload=insert_asset_reference(invite_id,aid,name,stored,folder);created.append(payload["id"]);schedule_media_derivatives(stored["path"],stored["mime"],stored.get("sha256",""));update_material_import_job(job_id,len(file_raw),True)
            except Exception as exc:
                failure={"name":name,"folder":folder,"error":str(exc)[:300]};failures.append(failure);update_material_import_job(job_id,max(0,int(info.file_size or 0)),False,failure)
        archive.close()
        with connect() as db:
            row=db.execute("SELECT status,processed_files,failed_files,processed_bytes FROM material_import_jobs WHERE id=?",(job_id,)).fetchone()
            if row and row["status"] not in {"cancelled","completed"}:db.execute("UPDATE material_import_jobs SET status='completed',updated_at=? WHERE id=?",(int(time.time()*1000),job_id))
        self.json(201,{"id":job_id,"status":"completed" if not failures else "completed-with-errors","createdAssetIds":created,"createdCount":len(created),"failedCount":len(failures),"failures":failures[:200],"rootName":root_name})

    def get_assets(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,name,mime,path,size,created_at,folder,tags_json,favorite,width,height,dominant_color FROM assets WHERE invitation_id=? ORDER BY favorite DESC,created_at DESC",(invite_id,)).fetchall()
        result=[]
        for r in rows:
            try: tags=json.loads(r["tags_json"] or "[]")
            except Exception: tags=[]
            result.append({"id":r["id"],"name":r["name"],"mime":r["mime"],"url":asset_public_url(r['path']),"size":r["size"],"createdAt":r["created_at"],"folder":r["folder"],"tags":tags,"favorite":bool(r["favorite"]),"width":r["width"],"height":r["height"],"dominantColor":r["dominant_color"],"responsiveBase":responsive_asset_url(r["path"])})
        self.json(200,result)

    def update_asset(self, asset_id):
        user=self.require_user()
        if not user:return
        data=self.body(30_000);name=str(data.get("name","")).strip()[:180];folder=sanitize_material_folder(data.get("folder","") or "");tags=data.get("tags",[]);favorite=1 if data.get("favorite") else 0
        if not name:raise ValueError("Material name is required")
        if not isinstance(tags,list) or len(tags)>30:raise ValueError("Invalid material tags")
        tags=[str(x).strip()[:60] for x in tags if str(x).strip()][:30]
        with connect() as db:
            row=db.execute("SELECT id,invitation_id FROM assets WHERE id=?",(asset_id,)).fetchone()
            if not row or not self.can_edit_invitation(db,row["invitation_id"],user["id"]):return self.json(404,{"error":"Material not found"})
            if folder:ensure_material_folder_chain(db,row["invitation_id"],user["id"],folder)
            db.execute("UPDATE assets SET name=?,folder=?,tags_json=?,favorite=? WHERE id=?",(name,folder,json.dumps(tags,ensure_ascii=False),favorite,asset_id))
        self.json(200,{"id":asset_id,"name":name,"folder":folder,"tags":tags,"favorite":bool(favorite)})

    def delete_asset(self, invite_id, asset_id):
        user=self.require_user()
        if not user:return
        purge=[]
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT path,sha256,object_id FROM assets WHERE id=? AND invitation_id=?",(asset_id,invite_id)).fetchone()
            if not row:return self.json(404,{"error":"Material not found"})
            db.execute("DELETE FROM assets WHERE id=? AND invitation_id=?",(asset_id,invite_id))
            if row["object_id"]:purge=release_stored_object_references(db,[row["object_id"]])
            elif not db.execute("SELECT 1 FROM assets WHERE path=? LIMIT 1",(row["path"],)).fetchone():purge=[(row["path"],row["sha256"])]
        queue_physical_deletions(purge)
        self.json(200,{"deleted":True})
    def _upload_claim(self, invite_id, asset_id, path, mime, size, expires):
        payload=f"{invite_id}|{asset_id}|{path}|{mime}|{int(size)}|{int(expires)}"
        signature=hmac.new(UPLOAD_SIGNING_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
        return {"assetId":asset_id,"path":path,"mime":mime,"size":int(size),"expires":int(expires),"signature":signature}
    def _verify_upload_claim(self, invite_id, claim):
        try:
            asset_id=str(claim.get("assetId",""));path=Path(str(claim.get("path",""))).name;mime=str(claim.get("mime",""));size=int(claim.get("size",0));expires=int(claim.get("expires",0));signature=str(claim.get("signature",""))
        except Exception:raise ValueError("Invalid upload claim")
        payload=f"{invite_id}|{asset_id}|{path}|{mime}|{int(size)}|{int(expires)}"
        valid=any(hmac.compare_digest(signature,hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()) for secret in (UPLOAD_SIGNING_SECRET,*UPLOAD_SIGNING_PREVIOUS_SECRETS))
        if expires<int(time.time()) or not valid:raise ValueError("Upload claim expired or invalid")
        if not asset_id or not path.startswith(asset_id):raise ValueError("Invalid upload path")
        return asset_id,path,mime,size
    def start_resumable_upload(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        if not self.rate_limit(f"upload-session:{user['id']}:{invite_id}",30,3600):return
        data=self.body(50_000);name=str(data.get("name","upload"))[:180] or "upload";mime,size=validate_material_request(str(data.get("mime","application/octet-stream")).lower(),int(data.get("size",0) or 0));folder=sanitize_material_folder(data.get("folder") or "");import_job_id=str(data.get("importJobId") or "")[:120]
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        if not self.require_plan_capacity(owner,"storageBytes",size):return
        session_id=str(uuid.uuid4());temp_name=f"upload-{session_id}.part";now=int(time.time()*1000);expires=now+24*60*60*1000
        (QUARANTINE/temp_name).write_bytes(b"")
        with connect() as db:db.execute("INSERT INTO upload_sessions(id,invitation_id,owner_id,name,mime,expected_size,received_size,temp_path,created_at,expires_at,folder,import_job_id) VALUES(?,?,?,?,?,?,0,?,?,?,?,?)",(session_id,invite_id,owner["id"],name,mime,size,temp_name,now,expires,folder,import_job_id))
        self.json(201,{"uploadId":session_id,"chunkSize":5_000_000,"received":0,"size":size,"expiresAt":expires})

    def get_upload_session(self, upload_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            row=db.execute("SELECT * FROM upload_sessions WHERE id=?",(upload_id,)).fetchone()
            if not row or not self.can_edit_invitation(db,row["invitation_id"],user["id"]):return self.json(404,{"error":"Upload session not found"})
        self.json(200,{"uploadId":row["id"],"invitationId":row["invitation_id"],"name":row["name"],"mime":row["mime"],"size":row["expected_size"],"received":row["received_size"],"expiresAt":row["expires_at"]})

    def append_upload_chunk(self, upload_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        size=int(self.headers.get("Content-Length","0") or 0)
        if size<=0 or size>5_500_000:raise ValueError("Upload chunk must be between 1 byte and 5.5 MB")
        try:offset=int(self.headers.get("X-Upload-Offset","-1"))
        except ValueError:raise ValueError("Invalid upload offset")
        with connect() as db:
            row=db.execute("SELECT * FROM upload_sessions WHERE id=?",(upload_id,)).fetchone()
            if not row or not self.can_edit_invitation(db,row["invitation_id"],user["id"]):return self.json(404,{"error":"Upload session not found"})
            if row["expires_at"]<=int(time.time()*1000):return self.json(410,{"error":"Upload session expired"})
            if offset!=int(row["received_size"]):return self.json(409,{"error":"Upload offset does not match the server","received":row["received_size"]})
            if offset+size>int(row["expected_size"]):raise ValueError("Upload chunk exceeds the expected file size")
            temp=QUARANTINE/Path(row["temp_path"]).name
            if not temp.exists():return self.json(410,{"error":"Upload session data is no longer available"})
            raw=self.rfile.read(size)
            if len(raw)!=size:raise ValueError("Upload chunk was incomplete")
            with temp.open("ab") as handle:handle.write(raw)
            received=offset+size;db.execute("UPDATE upload_sessions SET received_size=? WHERE id=?",(received,upload_id))
        self.json(200,{"uploadId":upload_id,"received":received,"complete":received==int(row["expected_size"])})

    def complete_resumable_upload(self, upload_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        with connect() as db:
            row=db.execute("SELECT * FROM upload_sessions WHERE id=?",(upload_id,)).fetchone()
            if not row or not self.can_edit_invitation(db,row["invitation_id"],user["id"]):return self.json(404,{"error":"Upload session not found"})
            owner=self.invitation_owner_user(db,row["invitation_id"])
        if not owner:return self.json(404,{"error":"Invitation not found"})
        if int(row["received_size"])!=int(row["expected_size"]):return self.json(409,{"error":"Upload is incomplete","received":row["received_size"],"size":row["expected_size"]})
        temp=QUARANTINE/Path(row["temp_path"]).name
        if not temp.is_file():return self.json(410,{"error":"Upload session data is no longer available"})
        raw=temp.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        with connect() as db:existing=db.execute("SELECT id FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime=? AND processing_state='ready' LIMIT 1",(owner["id"],digest,len(raw),row["mime"])).fetchone()
        if not existing and not self.require_plan_capacity(owner,"storageBytes",len(raw)):return
        asset_id=str(uuid.uuid4())
        try:
            stored=acquire_stored_object(owner["id"],asset_id,raw,row["mime"],scan_name=row["name"])
            payload=insert_asset_reference(row["invitation_id"],asset_id,row["name"],stored,row["folder"] if "folder" in row.keys() else "");payload["uploadMode"]="resumable"
            update_material_import_job(row["import_job_id"] if "import_job_id" in row.keys() else "",len(raw),True)
            schedule_media_derivatives(stored["path"],stored["mime"],stored.get("sha256",""))
            with connect() as db:db.execute("DELETE FROM upload_sessions WHERE id=?",(upload_id,))
            temp.unlink(missing_ok=True);self.json(201,payload)
        except Exception:
            # Validation/scanning failures should not leave abandoned chunks around.
            with connect() as db:db.execute("DELETE FROM upload_sessions WHERE id=?",(upload_id,))
            temp.unlink(missing_ok=True);raise

    def cancel_resumable_upload(self, upload_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            row=db.execute("SELECT invitation_id,temp_path FROM upload_sessions WHERE id=?",(upload_id,)).fetchone()
            if not row or not self.can_edit_invitation(db,row["invitation_id"],user["id"]):return self.json(404,{"error":"Upload session not found"})
            db.execute("DELETE FROM upload_sessions WHERE id=?",(upload_id,))
        try:(QUARANTINE/Path(row["temp_path"]).name).unlink(missing_ok=True)
        except OSError:pass
        self.json(200,{"cancelled":True})

    def presign_asset_upload(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        if not object_storage_enabled():return self.json(200,{"directUpload":False,"reason":"Object storage is not configured; use the authenticated application upload path."})
        if not self.rate_limit(f"upload-presign:{user['id']}:{invite_id}",120,3600):return
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        data=self.body(50_000);name=str(data.get("name","upload"))[:180] or "upload";mime=str(data.get("mime","application/octet-stream")).lower();size=int(data.get("size",0) or 0)
        allowed={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/gif":".gif","audio/mpeg":".mp3","audio/mp4":".m4a","video/mp4":".mp4","video/webm":".webm"}
        if mime not in allowed:raise ValueError("Unsupported material type")
        limit=50_000_000 if mime.startswith("video/") else 15_000_000
        if size<=0 or size>limit:raise ValueError(f"Material exceeds {limit//1_000_000} MB or is empty")
        if not self.require_plan_capacity(owner,"storageBytes",size):return
        asset_id=str(uuid.uuid4());path=asset_id+allowed[mime];expires=int(time.time())+15*60;claim=self._upload_claim(invite_id,asset_id,path,mime,size,expires)
        upload_url=object_storage_client().generate_presigned_url("put_object",Params={"Bucket":OBJECT_STORAGE_BUCKET,"Key":object_storage_key(path),"ContentType":mime,"CacheControl":"private,max-age=0,no-store"},ExpiresIn=15*60,HttpMethod="PUT")
        self.json(200,{"directUpload":True,"uploadUrl":upload_url,"headers":{"Content-Type":mime,"Cache-Control":"private,max-age=0,no-store"},"name":name,"claim":claim,"url":asset_public_url(path)})
    def complete_presigned_asset(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        if not object_storage_enabled():return self.json(409,{"error":"Direct object-storage upload is not configured"})
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        data=self.body(80_000);claim=data.get("claim") if isinstance(data.get("claim"),dict) else {};asset_id,path,mime,expected_size=self._verify_upload_claim(invite_id,claim);name=str(data.get("name","upload"))[:180] or "upload"
        head=object_storage_client().head_object(Bucket=OBJECT_STORAGE_BUCKET,Key=object_storage_key(path));actual_size=int(head.get("ContentLength",0) or 0)
        if actual_size!=expected_size:raise ValueError("Uploaded material size does not match the signed request")
        validate_material_request(mime,actual_size)
        raw=read_stored_asset_bytes(path)
        if raw is None or len(raw)!=actual_size:raise ValueError("Uploaded material could not be verified")
        digest=hashlib.sha256(raw).hexdigest()
        with connect() as db:duplicate_object=db.execute("SELECT id FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime=? AND processing_state='ready' LIMIT 1",(owner["id"],digest,actual_size,mime)).fetchone()
        if not duplicate_object and not self.require_plan_capacity(owner,"storageBytes",actual_size):
            delete_stored_asset(path,digest);return
        # Direct uploads are registered only after full signature, scan and image-safety validation.
        stored=register_existing_stored_object(owner["id"],path,raw,mime,name)
        payload=insert_asset_reference(invite_id,asset_id,name,stored);payload["directUpload"]=True
        schedule_media_derivatives(stored["path"],stored["mime"],stored.get("sha256",""))
        self.json(201,payload)
    def upload_font(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        if not self.rate_limit(f"font-upload:{user['id']}:{invite_id}",20,3600):return
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        size=int(self.headers.get("Content-Length","0") or 0)
        if size<=0:raise ValueError("The selected font is empty")
        if size>MAX_CUSTOM_FONT_SOURCE_BYTES:raise ValueError("Custom fonts must be 8 MB or smaller")
        if str(self.headers.get("X-Font-License-Acknowledged","")).strip().lower() not in {"1","true","yes"}:raise ValueError("Confirm that you have permission to use and publish this font")
        raw=self.rfile.read(size)
        if len(raw)!=size:raise ValueError("Font upload was incomplete")
        declared=str(self.headers.get("Content-Type","application/octet-stream")).split(";",1)[0].strip().lower()
        name=unquote(str(self.headers.get("X-File-Name","custom-font.ttf")))[:180] or "custom-font.ttf"
        optimized,metadata=optimize_custom_font(raw,name,declared)
        digest=hashlib.sha256(optimized).hexdigest();aid=str(uuid.uuid4())
        with connect() as db:existing=db.execute("SELECT id FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime='font/woff2' AND processing_state='ready' LIMIT 1",(owner["id"],digest,len(optimized))).fetchone()
        if not existing and not self.require_plan_capacity(owner,"storageBytes",len(optimized)):return
        safe_stem=re.sub(r"[^a-zA-Z0-9._-]+","-",Path(name).stem).strip("-.")[:70] or "custom-font"
        stored=acquire_stored_object(owner["id"],aid,optimized,"font/woff2",preferred_path=f"{aid}-{safe_stem}.woff2",scan_name=name,allow_font=True)
        payload=insert_asset_reference(invite_id,aid,name,stored)
        payload.update(metadata);payload.update({
            "mime":"font/woff2","sha256":stored.get("sha256",digest),
            "duplicate":bool(stored.get("duplicate")),"sourceMime":declared,
        })
        self.json(201,payload)

    def upload_raw(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        if not self.rate_limit(f"upload:{user['id']}:{invite_id}",60,3600): return
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        mime=str(self.headers.get("Content-Type","application/octet-stream")).split(";",1)[0].strip().lower();size=int(self.headers.get("Content-Length","0") or 0)
        validate_material_request(mime,size)
        raw=self.rfile.read(size)
        if len(raw)!=size:raise ValueError("Material upload was incomplete")
        name=unquote(str(self.headers.get("X-File-Name","upload")))[:180] or "upload";folder=sanitize_material_folder(unquote(str(self.headers.get("X-Material-Folder",""))));import_job_id=str(self.headers.get("X-Material-Import-Job","") or "")[:120];aid=str(uuid.uuid4())
        # Plan capacity is charged only when a new physical object is created.
        digest=hashlib.sha256(raw).hexdigest()
        with connect() as db:existing=db.execute("SELECT id FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime=? AND processing_state='ready' LIMIT 1",(owner["id"],digest,len(raw),mime)).fetchone()
        if not existing and not self.require_plan_capacity(owner,"storageBytes",len(raw)):return
        stored=acquire_stored_object(owner["id"],aid,raw,mime,scan_name=name)
        payload=insert_asset_reference(invite_id,aid,name,stored,folder)
        update_material_import_job(import_job_id,len(raw),True)
        schedule_media_derivatives(stored["path"],stored["mime"],stored.get("sha256",""))
        self.json(201,payload)
    def upload(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.require_upload_permission(user):return
        if not self.rate_limit(f"upload:{user['id']}:{invite_id}",60,3600): return
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            owner=self.invitation_owner_user(db,invite_id)
        if not owner:return self.json(404,{"error":"Invitation not found"})
        data=self.body(80_000_000);raw=base64.b64decode(data["base64"],validate=True);mime=str(data.get("mime","application/octet-stream")).lower();validate_material_request(mime,len(raw))
        aid=str(uuid.uuid4());digest=hashlib.sha256(raw).hexdigest()
        with connect() as db:existing=db.execute("SELECT id FROM stored_objects WHERE owner_id=? AND sha256=? AND size=? AND mime=? AND processing_state='ready' LIMIT 1",(owner["id"],digest,len(raw),mime)).fetchone()
        if not existing and not self.require_plan_capacity(owner,"storageBytes",len(raw)):return
        stored=acquire_stored_object(owner["id"],aid,raw,mime,scan_name=str(data.get("name","upload")))
        payload=insert_asset_reference(invite_id,aid,str(data.get("name","upload"))[:180],stored)
        schedule_media_derivatives(stored["path"],stored["mime"],stored.get("sha256",""))
        self.json(201,payload)
    def absolute_url(self, path):
        path=str(path or "")
        if re.match(r"^https?://",path,re.I):return path
        if PUBLIC_BASE_URL:return f"{PUBLIC_BASE_URL}{path if path.startswith('/') else '/'+path}"
        host=self.request_authority()
        if not host:return path
        direct=str(self.client_address[0] if self.client_address else "")
        forwarded_https=direct in TRUSTED_PROXY_IPS and self.headers.get("X-Forwarded-Proto","").lower()=="https"
        scheme="https" if COOKIE_SECURE or forwarded_https else "http"
        return f"{scheme}://{host}{path if path.startswith('/') else '/'+path}"

    def send_binary(self, status, body, content_type, cache_control="public,max-age=300", filename=None):
        self.send_response(status);self.send_header("Content-Type",content_type);self.send_header("Cache-Control",cache_control)
        if filename:self.send_header("Content-Disposition",f'inline; filename="{filename}"')
        self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

    def media_access_scope(self, path):
        clean=Path(str(path or "")).name
        if not clean:return None
        user=self.user();query=parse_qs(urlparse(self.path).query)
        invitation_id=str(query.get("i",[""])[0] or "");expires=query.get("exp",[""])[0];signature=query.get("sig",[""])[0]
        with connect() as db:
            rows=db.execute("SELECT DISTINCT a.invitation_id,i.access_mode,i.is_published,i.archived,i.gallery_access_password_hash FROM assets a JOIN invitations i ON i.id=a.invitation_id WHERE a.path=?",(clean,)).fetchall()
            if not rows:return None
            if user and any(self.can_read_invitation(db,row["invitation_id"],user["id"]) for row in rows):return "authenticated"
            if invitation_id and verify_media_signature(clean,invitation_id,expires,signature):
                signed_row=next((row for row in rows if row["invitation_id"]==invitation_id and row["is_published"] and not row["archived"]),None)
                if signed_row:return "signed"
            # Public immutable delivery is limited to a material that is actually
            # referenced by the latest published document of a non-password invitation.
            for row in rows:
                if not row["is_published"] or row["archived"] or row["access_mode"]=="password":continue
                publication=db.execute("SELECT document_json FROM publications WHERE invitation_id=? ORDER BY published_at DESC LIMIT 1",(row["invitation_id"],)).fetchone()
                if publication and document_references_media(publication["document_json"],clean):
                    if row["gallery_access_password_hash"]:
                        try:gallery_document=json.loads(publication["document_json"] or "{}")
                        except Exception:gallery_document={}
                        if (gallery_document.get("galleryProtection") or {}).get("enabled") and clean in protected_gallery_media_paths(gallery_document):continue
                    return "public"
        return None

    def send_media_binary(self, status, body, content_type, scope, etag="", modified_at=None, filename=None):
        etag_value=f'"{etag}"' if etag else f'"{hashlib.sha256(body).hexdigest()}"'
        if self.headers.get("If-None-Match","").strip()==etag_value:
            self.send_response(304);self.send_header("ETag",etag_value);self.end_headers();return
        cache_control="public,max-age=3600,must-revalidate" if scope=="public" else "private,max-age=60,must-revalidate" if scope=="signed" else "private,max-age=0,no-store"
        self.send_response(status);self.send_header("Content-Type",content_type);self.send_header("Cache-Control",cache_control);self.send_header("ETag",etag_value)
        if modified_at:
            stamp=float(modified_at)/1000 if float(modified_at)>10_000_000_000 else float(modified_at)
            self.send_header("Last-Modified",formatdate(stamp,usegmt=True))
        if filename:self.send_header("Content-Disposition",f'inline; filename="{filename}"')
        self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

    def serve_asset(self, path):
        clean=Path(str(path or "")).name
        if not clean:return self.json(404,{"error":"Material not found"})
        scope=self.media_access_scope(clean)
        if not scope:return self.json(403,{"error":"Material access is not authorized"})
        body=read_stored_asset_bytes(clean)
        if body is None:return self.json(404,{"error":"Material not found"})
        with connect() as db:meta=db.execute("SELECT sha256,mime,updated_at FROM stored_objects WHERE path=?",(clean,)).fetchone()
        content_type=(meta["mime"] if meta else None) or mimetypes.guess_type(clean)[0] or "application/octet-stream"
        digest=(meta["sha256"] if meta else "") or hashlib.sha256(body).hexdigest();modified=(meta["updated_at"] if meta else None)
        allowed,quota=bandwidth_delivery_allowed(clean,len(body))
        if not allowed:return self.json(429,{"error":"Media bandwidth quota exceeded","code":"bandwidth_quota","usage":quota})
        record_bandwidth_for_path(clean,len(body));return self.send_media_binary(200,body,content_type,scope,digest,modified,clean)

    def serve_responsive_image(self, path):
        clean=Path(str(path or "")).name
        if not clean:return self.json(404,{"error":"Image not found"})
        scope=self.media_access_scope(clean)
        if not scope:return self.json(403,{"error":"Image access is not authorized"})
        query=parse_qs(urlparse(self.path).query)
        try:width=int(query.get("w",[960])[0])
        except Exception:return self.json(400,{"error":"Invalid responsive image width","allowedWidths":list(IMAGE_WIDTH_ALLOWLIST)})
        if width not in IMAGE_WIDTH_ALLOWLIST:return self.json(400,{"error":"Unsupported responsive image width","allowedWidths":list(IMAGE_WIDTH_ALLOWLIST)})
        requested=str(query.get("format",["webp"])[0]).lower()
        if requested not in IMAGE_FORMAT_ALLOWLIST:return self.json(400,{"error":"Unsupported responsive image format","allowedFormats":sorted(IMAGE_FORMAT_ALLOWLIST)})
        if not self.rate_limit(f"image-derivative:{self.client_address[0]}:{clean}",180,60):return
        try:body,content_type,source_hash,modified=generate_image_derivative(clean,width,requested)
        except FileNotFoundError:return self.json(404,{"error":"Image not found"})
        except TypeError as exc:return self.json(415,{"error":str(exc)})
        except ValueError as exc:return self.json(400,{"error":str(exc)})
        etag=hashlib.sha256(f"{source_hash}|{width}|{derivative_format(requested)}".encode()).hexdigest()
        allowed,quota=bandwidth_delivery_allowed(clean,len(body))
        if not allowed:return self.json(429,{"error":"Media bandwidth quota exceeded","code":"bandwidth_quota","usage":quota})
        record_bandwidth_for_path(clean,len(body))
        return self.send_media_binary(200,body,content_type,scope,etag,modified,f"{Path(clean).stem}-{width}.{derivative_format(requested)}")

    def serve_signed_media(self, path):
        query=parse_qs(urlparse(self.path).query)
        if query.get("w") or query.get("format"):return self.serve_responsive_image(path)
        return self.serve_asset(path)

    def _published_social_document(self, slug):
        with connect() as db:
            row=db.execute("SELECT i.id,i.access_mode,p.document_json,p.version FROM invitations i LEFT JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? AND i.is_published=1 AND i.archived=0 AND i.deleted_at IS NULL AND (i.expires_at IS NULL OR i.expires_at>?) ORDER BY p.published_at DESC LIMIT 1",(slug,int(time.time()*1000))).fetchone()
        if not row:return None,None
        document={}
        if row["document_json"]:
            try:document=json.loads(row["document_json"])
            except Exception:document={}
        return row,document

    def social_card_svg(self, slug):
        row,d=self._published_social_document(slug)
        if not row:return self.json(404,{"error":"Invitation not found"})
        private=row["access_mode"]=="password";f=d.get("fields",{}) if not private else {};s=d.get("socialCard",{}) if not private else {};palette=d.get("palette",{}) if not private else {}
        title="Private Invitation" if private else str(f.get("namesKm") if s.get("language")=="km" else f.get("names") or "Invitation")[:120]
        date="" if private else str(f.get("date") or "")[:40];venue="" if private else str(f.get("venueKm") if s.get("language")=="km" else f.get("venue") or "")[:140]
        background=safe_hex_color(palette.get("background"),"#fff8f2");text=safe_hex_color(palette.get("text"),"#342c26");accent=safe_hex_color(d.get("accent"),"#9d4555");monogram=str(s.get("monogram") or d.get("openingScene",{}).get("monogram") or "")[:8]
        def x(value):return html.escape(str(value),quote=True)
        monogram_svg=(f'<text x="600" y="360" text-anchor="middle" fill="{x(accent)}" opacity=".10" font-family="Georgia,serif" font-size="280">{x(monogram)}</text>' if monogram else '')
        svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">'
             f'<rect width="1200" height="630" fill="{x(background)}"/><circle cx="1050" cy="90" r="220" fill="{x(accent)}" opacity=".12"/>'
             f'<circle cx="90" cy="600" r="260" fill="{x(accent)}" opacity=".08"/><rect x="54" y="46" width="1092" height="538" rx="28" fill="none" stroke="{x(accent)}" stroke-width="4"/>'
             f'<text x="600" y="150" text-anchor="middle" fill="{x(accent)}" font-family="Arial,sans-serif" font-size="30" letter-spacing="8">YOU ARE INVITED</text>{monogram_svg}'
             f'<text x="600" y="300" text-anchor="middle" fill="{x(text)}" font-family="Georgia,serif" font-size="76" font-weight="700">{x(title)}</text>'
             f'<text x="600" y="405" text-anchor="middle" fill="{x(text)}" font-family="Arial,sans-serif" font-size="32">{x(date)}</text>'
             f'<text x="600" y="465" text-anchor="middle" fill="{x(text)}" font-family="Arial,sans-serif" font-size="27">{x(venue)}</text></svg>')
        return self.send_binary(200,svg.encode("utf-8"),"image/svg+xml; charset=utf-8","public,max-age=300")

    def social_card_png(self, slug):
        row,d=self._published_social_document(slug)
        if not row:return self.json(404,{"error":"Invitation not found"})
        query=parse_qs(urlparse(self.path).query);fmt=str(query.get("format",["og"])[0]).lower()
        if fmt not in {"og","square","story"}:return self.json(400,{"error":"Unsupported social-card format"})
        cache=social_cache_path(row["id"],row["version"],fmt)
        try:
            if cache.exists():return self.send_binary(200,cache.read_bytes(),"image/png","public,max-age=300,must-revalidate",f"{slug}-{fmt}-social-card.png")
        except OSError:pass
        payload=render_social_card_png_bytes(row["id"],row["access_mode"],d,fmt)
        if payload is None:return self.social_card_svg(slug)
        try:
            tmp=cache.with_suffix(".tmp");tmp.write_bytes(payload);tmp.replace(cache)
        except OSError:pass
        return self.send_binary(200,payload,"image/png","public,max-age=300,must-revalidate",f"{slug}-{fmt}-social-card.png")

    def public_qr_png(self, slug):
        row,_=self._published_social_document(slug)
        if not row:return self.json(404,{"error":"Invitation not found"})
        clean_url=self.absolute_url(f"/i/{quote(slug)}");qr=make_qr_image(clean_url,10,4)
        if qr is None:return self.json(503,{"error":"QR generation support is not installed"})
        try:
            out=io.BytesIO();qr.save(out,"PNG",optimize=True)
            return self.send_binary(200,out.getvalue(),"image/png","public,max-age=300,must-revalidate",f"{slug}-qr.png")
        except Exception:return self.json(503,{"error":"QR image support requires Pillow and qrcode"})

    def public_qr_card_png(self, slug):
        row,d=self._published_social_document(slug)
        if not row:return self.json(404,{"error":"Invitation not found"})
        try:from PIL import Image,ImageDraw
        except Exception:return self.json(503,{"error":"QR image support requires Pillow"})
        clean_url=self.absolute_url(f"/i/{quote(slug)}");qr=make_qr_image(clean_url,10,4)
        if qr is None:return self.json(503,{"error":"QR generation support is not installed"})
        private=row["access_mode"]=="password";f=d.get("fields",{}) if not private else {};palette=d.get("palette",{}) if not private else {};accent=safe_hex_color(d.get("accent"),"#9d4555");background=safe_hex_color(palette.get("background"),"#fff8f2");text=safe_hex_color(palette.get("text"),"#342c26")
        canvas=Image.new("RGB",(1080,1080),background);draw=ImageDraw.Draw(canvas);draw.rounded_rectangle((58,58,1022,1022),radius=42,outline=accent,width=6)
        title="Private Invitation" if private else str(f.get("names") or "Invitation");title_font=image_font(54,text_is_khmer(title),True);title_lines=fitted_text_lines(draw,title,title_font,850,2) or ["Invitation"]
        title_y=112 if len(title_lines)>1 else 145
        for line in title_lines:draw.text((540,title_y),line,font=title_font,fill=text,anchor="mm");title_y+=62
        qr=qr.resize((620,620));canvas.paste(qr,(230,250));draw.text((540,920),"Scan to open the invitation",font=image_font(30,False,False),fill=text,anchor="mm")
        url_font=image_font(19,False,False);url_line=(fitted_text_lines(draw,clean_url,url_font,900,1) or [clean_url])[0];draw.text((540,968),url_line,font=url_font,fill=accent,anchor="mm")
        out=io.BytesIO();canvas.save(out,"PNG",optimize=True);return self.send_binary(200,out.getvalue(),"image/png","public,max-age=300",f"{slug}-qr.png")

    def guest_qr_png(self, invite_id, guest_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT g.id,g.name,g.token_salt,g.token_version,g.token_expires_at,g.token_revoked_at,i.slug FROM guests g JOIN invitations i ON i.id=g.invitation_id WHERE g.id=? AND g.invitation_id=?",(guest_id,invite_id)).fetchone()
        if not row:return self.json(404,{"error":"Guest not found"})
        if row["token_revoked_at"]:return self.json(409,{"error":"This personal link is revoked. Rotate the personal link before generating a QR code."})
        if row["token_expires_at"] and row["token_expires_at"]<=int(time.time()*1000):return self.json(409,{"error":"This personal link has expired. Rotate it before generating a QR code."})
        if not row["token_salt"]:return self.json(409,{"error":"This legacy guest needs a rotated personal link before QR generation."})
        token=guest_token_value(row["id"],row["token_salt"],row["token_version"] or 1)
        url=self.absolute_url(f"/i/{quote(row['slug'])}?g={quote(token)}");qr=make_qr_image(url,10,4)
        if qr is None:return self.json(503,{"error":"QR generation support is not installed"})
        try:
            out=io.BytesIO();qr.save(out,"PNG",optimize=True);return self.send_binary(200,out.getvalue(),"image/png","private,max-age=0,no-store",f"guest-{guest_id}-qr.png")
        except Exception:return self.json(503,{"error":"QR image support requires Pillow and qrcode"})

    def serve_public(self, slug):
        title="Invitation";description="You are invited to a special event."
        with connect() as db:
            row=db.execute("SELECT i.access_mode,p.document_json FROM invitations i LEFT JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? AND i.is_published=1 AND i.archived=0 AND i.deleted_at IS NULL AND (i.expires_at IS NULL OR i.expires_at>?) ORDER BY p.published_at DESC LIMIT 1",(slug,int(time.time()*1000))).fetchone()
            if row and row["access_mode"]!="password" and row["document_json"]:
                try:
                    document=json.loads(row["document_json"]);fields=document.get("fields",{});title=str(fields.get("names") or "Invitation")[:120];description=str(fields.get("message") or "You are invited to a special event.")[:240]
                except Exception:pass
            elif row and row["access_mode"]=="password":title="Private Invitation";description="A private invitation is waiting for you."
        image_format=available_social_image_format();image_path=f"/api/public/{quote(slug)}/social-card.{image_format}";public_path=f"/i/{quote(slug)}"
        page=(ROOT/"public.html").read_text(encoding="utf-8").replace('<head>','<head><meta name="einvite-backend" content="full"><base href="/">',1).replace("__INVITATION_SLUG__",slug).replace("__INVITATION_TITLE__",html.escape(title,quote=True)).replace("__INVITATION_DESCRIPTION__",html.escape(description,quote=True)).replace("__INVITATION_OG_IMAGE__",html.escape(self.absolute_url(image_path),quote=True)).replace("__INVITATION_OG_TYPE__","image/png" if image_format=="png" else "image/svg+xml").replace("__INVITATION_PUBLIC_URL__",html.escape(self.absolute_url(public_path),quote=True))
        body=page.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Cache-Control","no-cache"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

def ensure_frontend_assets():
    """Keep generated browser assets current without requiring a manual build locally.

    Production/public deployments are immutable: stale generated files stop startup
    with a useful error instead of modifying a deployed application directory.
    """
    steps=[
        ("editor bundle",[sys.executable,"build_editor_bundle.py","--check"],[sys.executable,"build_editor_bundle.py"]),
        ("route bundles",[sys.executable,"build_route_bundles.py","--check"],[sys.executable,"build_route_bundles.py"]),
        ("page manifest",[sys.executable,"build_page_manifests.py","--check"],[sys.executable,"build_page_manifests.py"]),
    ]
    rebuilt=False
    for label,check,build in steps:
        result=subprocess.run(check,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace")
        if result.returncode==0:continue
        detail=(result.stdout+result.stderr).strip()
        if PRODUCTION_MODE:
            raise RuntimeError(f"Generated {label} is stale. Run {' '.join(build[1:])} before deployment. {detail}")
        subprocess.run(build,cwd=ROOT,check=True)
        rebuilt=True
    if rebuilt:print("Frontend generated assets refreshed.",flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the E-invitation-website development server.")
    parser.add_argument("--host", default=os.environ.get("HOST","127.0.0.1"), help="Bind host (default: 127.0.0.1; use 0.0.0.0 for deployment)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT","4175")), help="HTTP port (default: 4175 or PORT environment variable)")
    args = parser.parse_args()
    display_host="127.0.0.1" if args.host in {"0.0.0.0","::"} else args.host
    address = f"http://{display_host}:{args.port}"
    print(f"E-invitation-website: {address}", flush=True)
    print(f"Data directory: {DATA}", flush=True)
    ensure_frontend_assets()
    platform_config=PlatformConfig.from_environment()
    platform_errors=list(platform_config.validate())
    if PRODUCTION_MODE:
        from production_preflight import validate_production_environment
        platform_errors=list(dict.fromkeys([*platform_errors,*validate_production_environment()]))
    if PRODUCTION_MODE and platform_errors:raise RuntimeError("Production configuration is invalid: "+" ".join(platform_errors))
    # Initialize and migrate once at process startup; ordinary SQLite connections stay lightweight.
    with connect() as _db:_db.execute("SELECT 1")
    ensure_agent_schema(connect)
    ensure_platform_schema(connect)
    cleanup_expired_security_rows()
    process_storage_delete_jobs(limit=100)
    cleanup_upload_sessions()
    cleanup_quarantine()
    evict_image_cache()
    class EInviteHTTPServer(ThreadingHTTPServer):
        allow_reuse_address=True
        daemon_threads=True
        block_on_close=False
        request_queue_size=64
        def __init__(self,*args,**kwargs):
            self.request_slots=threading.BoundedSemaphore(MAX_CONCURRENT_REQUESTS)
            super().__init__(*args,**kwargs)
        def process_request(self,request,client_address):
            if not self.request_slots.acquire(blocking=False):
                try:request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
                except OSError:pass
                self.shutdown_request(request);return
            try:super().process_request(request,client_address)
            except Exception:
                self.request_slots.release();raise
        def process_request_thread(self,request,client_address):
            try:super().process_request_thread(request,client_address)
            finally:self.request_slots.release()
        def handle_error(self,request,client_address):
            exc=sys.exc_info()[1]
            expected_disconnect=isinstance(exc,(BrokenPipeError,ConnectionResetError,ConnectionAbortedError)) or (isinstance(exc,OSError) and getattr(exc,'winerror',None) in {10053,10054})
            if expected_disconnect:return
            super().handle_error(request,client_address)
    server=EInviteHTTPServer((args.host,args.port),Handler)
    stopping=threading.Event()
    def backup_scheduler_loop():
        while not stopping.is_set():
            try:process_due_studio_backups(limit=3)
            except Exception as exc:
                if JSON_LOGS:print(json.dumps({"level":"warning","event":"studio_backup_scheduler_failed","message":str(exc)}),flush=True)
            if stopping.wait(60):break
    threading.Thread(target=backup_scheduler_loop,daemon=True,name="studio-backup-scheduler").start()
    def request_stop(*_):
        if stopping.is_set():return
        stopping.set();threading.Thread(target=server.shutdown,daemon=True).start()
    for sig in (getattr(signal,"SIGTERM",None),getattr(signal,"SIGINT",None),getattr(signal,"SIGBREAK",None)):
        if sig is not None:
            try:signal.signal(sig,request_stop)
            except (ValueError,OSError):pass
    try:server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        if _PLATFORM_V32_SERVICE is not None:
            try:_PLATFORM_V32_SERVICE.jobs.shutdown(timeout=10)
            except Exception:pass
        process_storage_delete_jobs(limit=100)
