"""Credential-free development backend for E-invitation-website."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs, quote
from pathlib import Path
import argparse, base64, hashlib, hmac, html, json, os, re, secrets, sqlite3, time, uuid, threading, smtplib, ssl, mimetypes, urllib.request, urllib.error
from http.cookies import SimpleCookie
from contextlib import contextmanager
from email.message import EmailMessage



def platform_env(name, default=None):
    """Read the current EINVITE_* setting, with legacy SOVAN_* fallback."""
    legacy = name.replace("EINVITE_", "SOVAN_", 1)
    return os.environ.get(name, os.environ.get(legacy, default))

ROOT = Path(__file__).resolve().parent
DATA = Path(platform_env("EINVITE_DATA_DIR", str(ROOT / "data"))).expanduser().resolve()
UPLOADS = DATA / "uploads"
DB = DATA / "invites.db"
OBJECT_STORAGE_BUCKET = platform_env("EINVITE_OBJECT_STORAGE_BUCKET", "").strip()
OBJECT_STORAGE_ENDPOINT = platform_env("EINVITE_OBJECT_STORAGE_ENDPOINT", "").strip() or None
OBJECT_STORAGE_REGION = platform_env("EINVITE_OBJECT_STORAGE_REGION", "auto").strip() or "auto"
OBJECT_STORAGE_ACCESS_KEY = platform_env("EINVITE_OBJECT_STORAGE_ACCESS_KEY", "").strip() or None
OBJECT_STORAGE_SECRET_KEY = platform_env("EINVITE_OBJECT_STORAGE_SECRET_KEY", "").strip() or None
OBJECT_STORAGE_PREFIX = platform_env("EINVITE_OBJECT_STORAGE_PREFIX", "materials/").strip().strip("/")
OBJECT_STORAGE_PUBLIC_BASE_URL = platform_env("EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL", "").strip().rstrip("/")
UPLOAD_SIGNING_SECRET = platform_env("EINVITE_UPLOAD_SIGNING_SECRET", "").strip() or secrets.token_urlsafe(32)
_S3_CLIENT = None

DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)

RATE_BUCKETS = {}
RATE_LOCK = threading.Lock()

PLAN_LIMITS = {
    "free": {"invitations": 3, "templates": 5, "storageBytes": 250_000_000},
    "creator": {"invitations": 50, "templates": 100, "storageBytes": 5_000_000_000},
    "studio": {"invitations": 500, "templates": 1000, "storageBytes": 50_000_000_000},
}
PLAN_LIMITS_ENFORCED = platform_env("EINVITE_ENFORCE_PLAN_LIMITS", "0").lower() in {"1", "true", "yes"}
STARTED_AT = time.time()
SESSION_COOKIE_NAME = platform_env("EINVITE_SESSION_COOKIE_NAME", "einvite_session").strip() or "einvite_session"
COOKIE_SECURE = platform_env("EINVITE_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
AI_ENDPOINT = platform_env("EINVITE_AI_ENDPOINT", "").strip()
AI_API_KEY = platform_env("EINVITE_AI_API_KEY", "").strip()
AI_MODEL = platform_env("EINVITE_AI_MODEL", "").strip()
AI_TIMEOUT = max(2, min(60, int(platform_env("EINVITE_AI_TIMEOUT", "20"))))
BILLING_WEBHOOK_SECRET = platform_env("EINVITE_BILLING_WEBHOOK_SECRET", "").strip()
BILLING_CHECKOUT_ENDPOINT = platform_env("EINVITE_BILLING_CHECKOUT_ENDPOINT", "").strip()
BILLING_API_KEY = platform_env("EINVITE_BILLING_API_KEY", "").strip()
JSON_LOGS = platform_env("EINVITE_JSON_LOGS", "0").lower() in {"1", "true", "yes"}
REDIS_URL = platform_env("EINVITE_REDIS_URL", "").strip()
_REDIS_CLIENT = None
DATABASE_URL = platform_env("EINVITE_DATABASE_URL", "").strip()
DATABASE_KIND = "postgresql" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"
PUBLIC_BASE_URL = platform_env("EINVITE_PUBLIC_BASE_URL", "").strip().rstrip("/")

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

def auth_action_url(path, token):
    base=platform_env("EINVITE_PUBLIC_BASE_URL","").rstrip("/")
    return f"{base}{path}?token={token}" if base else f"{path}?token={token}"

def object_storage_enabled():
    return bool(OBJECT_STORAGE_BUCKET)

def object_storage_key(path):
    clean=str(path or "").lstrip("/")
    return f"{OBJECT_STORAGE_PREFIX}/{clean}" if OBJECT_STORAGE_PREFIX else clean

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
    if OBJECT_STORAGE_PUBLIC_BASE_URL:return f"{OBJECT_STORAGE_PUBLIC_BASE_URL}/{quote(object_storage_key(path),safe='/')}"
    return f"/uploads/{quote(str(path),safe='')}"

def store_asset_bytes(path,raw,mime):
    if object_storage_enabled():
        object_storage_client().put_object(Bucket=OBJECT_STORAGE_BUCKET,Key=object_storage_key(path),Body=raw,ContentType=mime,CacheControl="public,max-age=31536000,immutable")
    else:(UPLOADS/path).write_bytes(raw)

def delete_stored_asset(path):
    if object_storage_enabled():
        try:object_storage_client().delete_object(Bucket=OBJECT_STORAGE_BUCKET,Key=object_storage_key(path))
        except Exception as exc:print(f"Object-storage delete failed for {path}: {exc}",flush=True)
    else:
        local=UPLOADS/path
        if local.exists():local.unlink()

def validate_document(document):
    if not isinstance(document, dict): raise ValueError("Invitation document must be an object")
    encoded = json.dumps(document, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 5_000_000: raise ValueError("Invitation document exceeds 5 MB")
    objects = document.get("objects", {})
    if not isinstance(objects, dict) or len(objects) > 300: raise ValueError("Invitation contains too many design objects")
    allowed_animations = {"fade-up", "soft-zoom", "slide-left", "blur-in", "bounce-in", "flip-in", "float", "none"}
    dimension_pattern = re.compile(r"^-?\d+(?:\.\d+)?(?:%|px)?$")
    for object_id, obj in objects.items():
        if not isinstance(object_id, str) or len(object_id) > 120 or not isinstance(obj, dict): raise ValueError("Invalid design object")
        if obj.get("type") not in (None, "text", "image", "shape", "decoration"): raise ValueError("Unsupported design object type")
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
        try: font_size = float(obj.get("fontSize", 0) or 0)
        except (TypeError, ValueError): raise ValueError("Invalid object font size")
        if not 0 <= font_size <= 200: raise ValueError("Invalid object font size")
        if obj.get("textAlign", "center") not in {"left", "center", "right"}: raise ValueError("Invalid text alignment")
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
        if not isinstance(page_objects, dict) or len(page_objects) > 300: raise ValueError("Visual page contains too many design objects")
        if page.get("useMasterBackground", False) not in (True, False): raise ValueError("Invalid page master background setting")
        transition=page.get("transition", {}) or {}
        if not isinstance(transition, dict) or transition.get("preset", "soft") not in {"none","soft","overlap","sweep"}: raise ValueError("Invalid page transition")
        try: transition_duration=float(transition.get("duration",600))
        except (TypeError,ValueError): raise ValueError("Invalid page transition duration")
        if not 200 <= transition_duration <= 2000: raise ValueError("Invalid page transition duration")
        validate_document({"objects": page_objects})
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
    allowed_sections = {"gallery", "video", "countdown", "schedule", "custom", "venue", "contact", "rsvp", "wishes"}
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

@contextmanager
def connect_sqlite():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA foreign_keys=ON")
    try:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, salt TEXT NOT NULL, created_at INTEGER NOT NULL, role TEXT NOT NULL DEFAULT 'customer', email_verified INTEGER NOT NULL DEFAULT 0, plan TEXT NOT NULL DEFAULT 'free');
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS invitations(id TEXT PRIMARY KEY, slug TEXT UNIQUE NOT NULL, draft_json TEXT NOT NULL, updated_at INTEGER NOT NULL, owner_id TEXT, archived INTEGER NOT NULL DEFAULT 0, views INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, version INTEGER NOT NULL, document_json TEXT NOT NULL, published_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS rsvps(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL, guest_count INTEGER NOT NULL, note TEXT, created_at INTEGER NOT NULL, answers_json TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, created_at INTEGER NOT NULL, folder TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]', favorite INTEGER NOT NULL DEFAULT 0, sha256 TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS guests(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, name TEXT NOT NULL, phone TEXT, token TEXT UNIQUE NOT NULL, created_at INTEGER NOT NULL, checked_in INTEGER NOT NULL DEFAULT 0, checked_in_at INTEGER);
        CREATE TABLE IF NOT EXISTS user_templates(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, document_json TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, description TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]', favorite INTEGER NOT NULL DEFAULT 0, current_version INTEGER NOT NULL DEFAULT 1, thumbnail_json TEXT NOT NULL DEFAULT '{}', visibility TEXT NOT NULL DEFAULT 'private', published_at INTEGER);
        CREATE TABLE IF NOT EXISTS template_versions(id TEXT PRIMARY KEY, template_id TEXT NOT NULL, version INTEGER NOT NULL, document_json TEXT NOT NULL, created_at INTEGER NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_template_versions_unique ON template_versions(template_id,version);
        CREATE TABLE IF NOT EXISTS user_page_templates(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'General', page_json TEXT NOT NULL, favorite INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS view_events(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, viewed_at INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_view_events_invitation ON view_events(invitation_id,viewed_at);
        CREATE TABLE IF NOT EXISTS access_tokens(token_hash TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS user_components(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'General', payload_json TEXT NOT NULL, favorite INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS guest_messages(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL, publication_id TEXT NOT NULL, name TEXT NOT NULL, message TEXT NOT NULL, created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_tokens(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS invitation_collaborators(invitation_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'viewer', created_at INTEGER NOT NULL, PRIMARY KEY(invitation_id,user_id));
        CREATE INDEX IF NOT EXISTS idx_invitation_collaborators_user ON invitation_collaborators(user_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_kind ON auth_tokens(user_id,kind,expires_at);
        CREATE INDEX IF NOT EXISTS idx_user_components_owner_kind ON user_components(owner_id,kind,updated_at);
        """)
        user_columns={row["name"] for row in db.execute("PRAGMA table_info(users)")}
        if "role" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'customer'")
        if "email_verified" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        if "plan" not in user_columns: db.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
        columns={row["name"] for row in db.execute("PRAGMA table_info(invitations)")}
        if "owner_id" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN owner_id TEXT")
        if "archived" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
        if "views" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN views INTEGER NOT NULL DEFAULT 0")
        if "access_mode" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN access_mode TEXT NOT NULL DEFAULT 'unlisted'")
        if "access_password_hash" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN access_password_hash TEXT")
        if "access_password_salt" not in columns: db.execute("ALTER TABLE invitations ADD COLUMN access_password_salt TEXT")
        if "is_published" not in columns:
            db.execute("ALTER TABLE invitations ADD COLUMN is_published INTEGER NOT NULL DEFAULT 0")
            db.execute("UPDATE invitations SET is_published=1 WHERE EXISTS(SELECT 1 FROM publications p WHERE p.invitation_id=invitations.id)")
        guest_columns={row["name"] for row in db.execute("PRAGMA table_info(guests)")}
        if "checked_in" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN checked_in INTEGER NOT NULL DEFAULT 0")
        if "checked_in_at" not in guest_columns: db.execute("ALTER TABLE guests ADD COLUMN checked_in_at INTEGER")
        rsvp_columns={row["name"] for row in db.execute("PRAGMA table_info(rsvps)")}
        if "answers_json" not in rsvp_columns: db.execute("ALTER TABLE rsvps ADD COLUMN answers_json TEXT NOT NULL DEFAULT '{}'")
        asset_columns={row["name"] for row in db.execute("PRAGMA table_info(assets)")}
        if "folder" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN folder TEXT NOT NULL DEFAULT ''")
        if "tags_json" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'")
        if "favorite" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
        if "sha256" not in asset_columns: db.execute("ALTER TABLE assets ADD COLUMN sha256 TEXT NOT NULL DEFAULT ''")
        template_columns={row["name"] for row in db.execute("PRAGMA table_info(user_templates)")}
        for column,definition in {
            "description":"TEXT NOT NULL DEFAULT ''",
            "tags_json":"TEXT NOT NULL DEFAULT '[]'",
            "favorite":"INTEGER NOT NULL DEFAULT 0",
            "current_version":"INTEGER NOT NULL DEFAULT 1",
            "thumbnail_json":"TEXT NOT NULL DEFAULT '{}'",
            "visibility":"TEXT NOT NULL DEFAULT 'private'",
            "published_at":"INTEGER",
        }.items():
            if column not in template_columns: db.execute(f"ALTER TABLE user_templates ADD COLUMN {column} {definition}")
        # Backfill version history for templates created before versioning existed.
        for row in db.execute("SELECT id,document_json,current_version,created_at FROM user_templates").fetchall():
            if not db.execute("SELECT 1 FROM template_versions WHERE template_id=? LIMIT 1",(row["id"],)).fetchone():
                version=max(1,int(row["current_version"] or 1));db.execute("INSERT OR IGNORE INTO template_versions(id,template_id,version,document_json,created_at) VALUES(?,?,?,?,?)",(str(uuid.uuid4()),row["id"],version,row["document_json"],row["created_at"]))
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
    }
    check = signatures.get(mime)
    if not check or not check(raw): raise ValueError("Uploaded material content does not match its declared file type")
    return raw

def clean_slug(value):
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return value[:60] or "our-invitation"

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),210_000).hex()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT), **kwargs)
    def log_message(self, format, *args):
        # Keep request handling independent from a terminal that may be closed.
        if JSON_LOGS:
            try:
                print(json.dumps({"ts":int(time.time()*1000),"client":self.client_address[0],"method":getattr(self,"command",None),"path":getattr(self,"path",None),"message":format%args},ensure_ascii=False),flush=True)
            except Exception:pass
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-site")
        if COOKIE_SECURE:self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline' https://www.youtube.com https://www.youtube-nocookie.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; media-src 'self' data: blob: https:; font-src 'self' data: https:; frame-src https://www.youtube.com https://www.youtube-nocookie.com; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'")
        super().end_headers()
    def json(self, status, value, headers=None):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body)))
        for key,val in (headers or {}).items():self.send_header(key,val)
        self.end_headers(); self.wfile.write(body)
    def guard_cookie_origin(self):
        """Reject cross-site state changes when browser cookie authentication is present.

        SameSite=Lax already blocks most CSRF, while this Origin check adds a second layer
        without affecting CLI/API clients that authenticate with Bearer tokens only.
        """
        if not self.cookie_token():return True
        origin=(self.headers.get("Origin") or "").strip()
        if not origin:return True
        host=(self.headers.get("Host") or "").strip()
        allowed={f"http://{host}",f"https://{host}"}
        if PUBLIC_BASE_URL:
            try:
                parsed=urlparse(PUBLIC_BASE_URL);allowed.add(f"{parsed.scheme}://{parsed.netloc}")
            except Exception:pass
        if origin.rstrip("/") not in {x.rstrip("/") for x in allowed if x}:
            self.json(403,{"error":"Cross-site request rejected"});return False
        return True

    def body(self, limit=20_000_000):
        size = int(self.headers.get("Content-Length", "0"))
        if size > limit: raise ValueError("Request too large")
        return json.loads(self.rfile.read(size) or b"{}")
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
        for value in (self.bearer_token(),self.cookie_token()):
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
                row=db.execute("SELECT u.id,u.email,u.role,u.email_verified,u.plan FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?",(token_hash,now)).fetchone()
                if row:return row
        return None
    def require_user(self):
        user=self.user()
        if not user:self.json(401,{"error":"Authentication required"})
        return user
    def require_role(self,*roles):
        user=self.require_user()
        if not user:return None
        if user["role"] not in roles:self.json(403,{"error":"Insufficient permissions"});return None
        return user
    def owns(self, db, invite_id, user_id):
        return db.execute("SELECT 1 FROM invitations WHERE id=? AND owner_id=?",(invite_id,user_id)).fetchone() is not None
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
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health": return self.json(200, {"ok": True, "database": DATABASE_KIND, "assetStorage": "object" if object_storage_enabled() else "local", "planLimitsEnforced": PLAN_LIMITS_ENFORCED, "redis": bool(redis_client()), "aiConfigured": bool(AI_ENDPOINT), "smtpConfigured": bool(platform_env("EINVITE_SMTP_HOST","").strip() and platform_env("EINVITE_MAIL_FROM","").strip()), "billingWebhookConfigured": bool(BILLING_WEBHOOK_SECRET), "billingCheckoutConfigured": bool(BILLING_CHECKOUT_ENDPOINT), "uptimeSeconds": int(time.time()-STARTED_AT)})
        if path == "/api/admin/metrics": return self.admin_system_metrics()
        if path == "/api/auth/me":
            user=self.user(); return self.json(200,{"user":dict(user) if user else None})
        if path == "/api/account/export": return self.export_account()
        if path == "/api/account/usage": return self.account_usage()
        if path == "/api/admin/overview": return self.admin_overview()
        if path == "/api/admin/users": return self.admin_users()
        if path == "/api/admin/templates": return self.admin_templates()
        if path == "/api/admin/invitations": return self.admin_invitations()
        if path == "/api/invitations": return self.list_invitations()
        if path == "/api/template-marketplace": return self.list_marketplace_templates()
        if path.startswith("/api/template-marketplace/") and path.count("/") == 3: return self.get_marketplace_template(path.split("/")[3])
        if path == "/api/templates": return self.list_templates()
        if path == "/api/page-templates": return self.list_page_templates()
        if path == "/api/components": return self.list_components()
        if path.startswith("/api/templates/") and path.endswith("/versions"): return self.get_template_versions(path.split("/")[3])
        if path.startswith("/api/templates/") and path.count("/") == 3: return self.get_template(path.split("/")[3])
        if path == "/api/assets": return self.get_account_assets()
        if path.startswith("/api/invitations/") and path.endswith("/assets"): return self.get_assets(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.count("/") == 3: return self.get_invitation(path.split("/")[3])
        if path.startswith("/i/"): return self.serve_public(path.split("/", 2)[2])
        if path.startswith("/api/public/"):
            query=parse_qs(urlparse(self.path).query);guest=query.get("guest",[None])[0];access=query.get("access",[None])[0]
            return self.get_public(unquote(path.split("/", 3)[3]),guest,access)
        if path.startswith("/api/invitations/") and path.endswith("/guests"): return self.get_guests(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/rsvps"): return self.get_rsvps(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/versions"): return self.get_versions(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/analytics"): return self.get_analytics(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/wishes"): return self.get_wishes(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/collaborators"): return self.get_collaborators(path.split("/")[3])
        if path.startswith("/api/invitations/") and path.endswith("/events"): return self.invitation_events(path.split("/")[3])
        if path.startswith("/uploads/"):return self.serve_asset(unquote(path[len("/uploads/"):]))
        return super().do_GET()
    def do_PUT(self):
        if not self.guard_cookie_origin():return
        path = urlparse(self.path).path
        try:
            if path == "/api/auth/password": return self.change_password()
            if path.startswith("/api/assets/") and path.count("/") == 3: return self.update_asset(path.split("/")[3])
            if path.startswith("/api/admin/users/") and path.endswith("/role"): return self.admin_update_user_role(path.split("/")[4])
            if path.startswith("/api/admin/users/") and path.endswith("/plan"): return self.admin_update_user_plan(path.split("/")[4])
            if path.startswith("/api/admin/templates/") and path.endswith("/visibility"): return self.admin_update_template_visibility(path.split("/")[4])
            if path.startswith("/api/admin/invitations/") and path.endswith("/published"): return self.admin_update_invitation_published(path.split("/")[4])
            if "/guests/" in path and path.endswith("/check-in"): return self.check_in_guest(path.split("/")[3],path.split("/")[5])
            if "/rsvps/" in path: return self.update_rsvp(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/templates/") and path.count("/") == 3: return self.update_template(path.split("/")[3])
            if path.startswith("/api/page-templates/") and path.count("/") == 3: return self.update_page_template(path.split("/")[3])
            if path.startswith("/api/components/") and path.count("/") == 3: return self.update_component(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/archive"): return self.archive_invitation(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/slug"): return self.update_slug(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/access"): return self.update_access(path.split("/")[3])
            if path.startswith("/api/invitations/"): return self.save_draft(path.split("/")[3])
            self.json(404, {"error": "Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.json(400, {"error": str(exc)})
    def do_DELETE(self):
        if not self.guard_cookie_origin():return
        path=urlparse(self.path).path
        try:
            if "/assets/" in path:return self.delete_asset(path.split("/")[3],path.split("/")[5])
            if "/guests/" in path:return self.delete_guest(path.split("/")[3],path.split("/")[5])
            if "/rsvps/" in path:return self.delete_rsvp(path.split("/")[3],path.split("/")[5])
            if "/wishes/" in path:return self.delete_wish(path.split("/")[3],path.split("/")[5])
            if "/collaborators/" in path:return self.delete_collaborator(path.split("/")[3],path.split("/")[5])
            if path.startswith("/api/page-templates/"): return self.delete_page_template(path.split("/")[3])
            if path.startswith("/api/components/"): return self.delete_component(path.split("/")[3])
            if path.startswith("/api/templates/"): return self.delete_template(path.split("/")[3])
            if path.startswith("/api/invitations/"): return self.delete_invitation(path.split("/")[3])
            self.json(404,{"error":"Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.json(400, {"error": str(exc)})
    def do_POST(self):
        if not self.guard_cookie_origin():return
        path = urlparse(self.path).path
        try:
            if path == "/api/auth/register": return self.register()
            if path == "/api/auth/login": return self.login()
            if path == "/api/auth/logout": return self.logout()
            if path == "/api/auth/password-reset/request": return self.request_password_reset()
            if path == "/api/auth/password-reset/confirm": return self.confirm_password_reset()
            if path == "/api/auth/verification/request": return self.request_email_verification()
            if path == "/api/auth/verification/confirm": return self.confirm_email_verification()
            if path == "/api/ai/assist": return self.ai_assist()
            if path == "/api/billing/webhook": return self.billing_webhook()
            if path == "/api/billing/checkout": return self.billing_checkout()
            if path == "/api/invitations": return self.create_invitation()
            if path == "/api/templates": return self.create_template()
            if path == "/api/page-templates": return self.create_page_template()
            if path == "/api/components": return self.create_component()
            if path.startswith("/api/templates/") and path.endswith("/duplicate"): return self.duplicate_template(path.split("/")[3])
            if path.startswith("/api/templates/") and path.endswith("/restore"): return self.restore_template_version(path.split("/")[3])
            if path.startswith("/api/public/") and path.endswith("/unlock"): return self.unlock_public(unquote(path.split("/")[3]))
            if path.startswith("/api/invitations/") and path.endswith("/publish"): return self.publish(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/unpublish"): return self.unpublish(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets/presign"): return self.presign_asset_upload(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets/complete"): return self.complete_presigned_asset(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets/raw"): return self.upload_raw(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/assets"): return self.upload(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/guests"): return self.add_guest(path.split("/")[3])
            if path.startswith("/api/invitations/") and path.endswith("/collaborators"): return self.add_collaborator(path.split("/")[3])
            if path.startswith("/api/public/") and path.endswith("/wishes"): return self.submit_wish(unquote(path.split("/")[3]))
            if path.startswith("/api/public/") and path.endswith("/rsvps"): return self.rsvp(unquote(path.split("/")[3]))
            self.json(404, {"error": "Not found"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc: self.json(400, {"error": str(exc)})
    def local_ai_response(self, task, prompt, context):
        prompt=str(prompt or "").strip();context=context if isinstance(context,dict) else {}
        names=str(context.get("names") or "the hosts").strip();event_type=str(context.get("eventType") or "event").strip().lower();venue=str(context.get("venue") or "").strip();date=str(context.get("date") or "").strip()
        if task=="translate-km":return f"សូមគោរពអញ្ជើញលោកអ្នកចូលរួមអបអរសាទរ{('ពិធីមង្គលការ' if event_type=='wedding' else 'កម្មវិធីពិសេស')}របស់ {names}។ វត្តមានរបស់លោកអ្នកនឹងធ្វើឱ្យឱកាសដ៏ពិសេសនេះកាន់តែមានន័យ។"
        if task=="translate-en":return f"You are warmly invited to celebrate this special {event_type} with {names}. Your presence would make the occasion even more meaningful."
        if task=="formal":return f"Together with our families, {names} respectfully request the pleasure of your company at our {event_type}{(' on '+date) if date else ''}{(' at '+venue) if venue else ''}."
        if task=="romantic":return f"With joyful hearts, {names} invite you to share a beautiful beginning filled with love, laughter, and memories we will cherish forever."
        if task=="shorten":return (prompt[:180].rsplit(' ',1)[0]+'…') if len(prompt)>190 else (prompt or f"Join {names} for a beautiful celebration.")
        if task=="schedule":return "4:00 PM — Guest arrival\n5:00 PM — Welcome and ceremony\n6:30 PM — Dinner reception\n8:00 PM — Celebration and photos"
        if task=="design":return "Use one strong hero photograph, a restrained two-color palette, an elegant display typeface for names, a clean sans-serif for details, generous spacing, and a clear flow from invitation → schedule → venue → RSVP."
        return prompt or f"Together with our families, {names} warmly invite you to celebrate our special {event_type}. We would be honored to share this meaningful occasion with you."

    def ai_assist(self):
        user=self.require_user()
        if not user:return
        if not self.rate_limit(f"ai:{user['id']}",60,3600):return
        data=self.body(300_000);task=str(data.get("task","") or "write")[:80];prompt=str(data.get("prompt","") or "")[:20_000];context=data.get("context",{})
        if not isinstance(context,dict):context={}
        if AI_ENDPOINT:
            payload=json.dumps({"task":task,"prompt":prompt,"context":context,"model":AI_MODEL or None},ensure_ascii=False).encode()
            headers={"Content-Type":"application/json","User-Agent":"E-invitation-website/1.0"}
            if AI_API_KEY:headers["Authorization"]=f"Bearer {AI_API_KEY}"
            try:
                request=urllib.request.Request(AI_ENDPOINT,data=payload,headers=headers,method="POST")
                with urllib.request.urlopen(request,timeout=AI_TIMEOUT) as response:result=json.loads(response.read(2_000_000) or b"{}")
                text=result.get("text") or result.get("output") or result.get("output_text")
                if not text and isinstance(result.get("choices"),list) and result["choices"]:
                    first=result["choices"][0];text=((first.get("message") or {}).get("content") if isinstance(first,dict) else None) or (first.get("text") if isinstance(first,dict) else None)
                if isinstance(text,list):text="\n".join(str(x.get("text",x) if isinstance(x,dict) else x) for x in text)
                if text:return self.json(200,{"text":str(text)[:50_000],"provider":"external"})
            except Exception as exc:
                if JSON_LOGS:print(json.dumps({"level":"warning","event":"ai_provider_failed","message":str(exc)}),flush=True)
        return self.json(200,{"text":self.local_ai_response(task,prompt,context),"provider":"local"})

    def billing_checkout(self):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);plan=str(data.get("plan","")).lower()
        if plan not in {"creator","studio"}:raise ValueError("Unsupported checkout plan")
        if not BILLING_CHECKOUT_ENDPOINT:return self.json(503,{"error":"Automatic checkout is not configured yet"})
        payload=json.dumps({"userId":user["id"],"email":user["email"],"plan":plan,"returnUrl":platform_env("EINVITE_PUBLIC_BASE_URL","").rstrip("/")+"/billing.html"},ensure_ascii=False).encode()
        headers={"Content-Type":"application/json","User-Agent":"E-invitation-website/1.0"}
        if BILLING_API_KEY:headers["Authorization"]=f"Bearer {BILLING_API_KEY}"
        try:
            request=urllib.request.Request(BILLING_CHECKOUT_ENDPOINT,data=payload,headers=headers,method="POST")
            with urllib.request.urlopen(request,timeout=20) as response:result=json.loads(response.read(1_000_000) or b"{}")
            url=str(result.get("url") or result.get("checkoutUrl") or result.get("checkout_url") or "")
            if not re.match(r"^https://",url,re.I):raise ValueError("Billing provider returned an invalid checkout URL")
            return self.json(200,{"url":url,"plan":plan})
        except urllib.error.HTTPError as exc:
            try:message=json.loads(exc.read() or b"{}").get("error")
            except Exception:message=None
            return self.json(502,{"error":message or "Billing provider checkout failed"})
        except Exception as exc:
            return self.json(502,{"error":f"Billing provider checkout failed: {exc}"})

    def billing_webhook(self):
        if not BILLING_WEBHOOK_SECRET:return self.json(503,{"error":"Billing webhook is not configured"})
        size=int(self.headers.get("Content-Length","0"));
        if size<=0 or size>500_000:raise ValueError("Invalid webhook payload")
        raw=self.rfile.read(size);signature=self.headers.get("X-EInvite-Signature","").strip().lower()
        expected=hmac.new(BILLING_WEBHOOK_SECRET.encode(),raw,hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature,expected):return self.json(401,{"error":"Invalid webhook signature"})
        data=json.loads(raw or b"{}");event=str(data.get("type","")).lower();payload=data.get("data") if isinstance(data.get("data"),dict) else data
        user_id=str(payload.get("userId","") or "");email=str(payload.get("email","") or "").strip().lower();plan=str(payload.get("plan","") or "free").lower()
        if event in {"subscription.cancelled","subscription.canceled"}:plan="free"
        if event not in {"subscription.updated","subscription.created","subscription.cancelled","subscription.canceled"}:return self.json(202,{"received":True,"ignored":True})
        if plan not in PLAN_LIMITS:raise ValueError("Unsupported plan")
        with connect() as db:
            row=db.execute("SELECT id FROM users WHERE id=? OR email=? LIMIT 1",(user_id,email)).fetchone()
            if not row:return self.json(202,{"received":True,"matched":False})
            db.execute("UPDATE users SET plan=? WHERE id=?",(plan,row["id"]))
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

    def admin_overview(self):
        user=self.require_role("admin")
        if not user:return
        with connect() as db:
            counts={
                "users":db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
                "invitations":db.execute("SELECT COUNT(*) c FROM invitations").fetchone()["c"],
                "publishedInvitations":db.execute("SELECT COUNT(*) c FROM invitations WHERE is_published=1").fetchone()["c"],
                "templates":db.execute("SELECT COUNT(*) c FROM user_templates").fetchone()["c"],
                "marketplaceTemplates":db.execute("SELECT COUNT(*) c FROM user_templates WHERE visibility='public'").fetchone()["c"],
                "rsvps":db.execute("SELECT COUNT(*) c FROM rsvps").fetchone()["c"],
                "assets":db.execute("SELECT COUNT(*) c FROM assets").fetchone()["c"],
            }
        self.json(200,counts)

    def admin_users(self):
        user=self.require_role("admin")
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT u.id,u.email,u.role,u.plan,u.created_at,(SELECT COUNT(*) FROM invitations i WHERE i.owner_id=u.id) invitation_count,(SELECT COUNT(*) FROM user_templates t WHERE t.owner_id=u.id) template_count FROM users u ORDER BY u.created_at DESC LIMIT 1000").fetchall()
        self.json(200,[{"id":r["id"],"email":r["email"],"role":r["role"],"plan":r["plan"],"createdAt":r["created_at"],"invitationCount":r["invitation_count"],"templateCount":r["template_count"]} for r in rows])

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

    def admin_update_template_visibility(self,template_id):
        admin=self.require_role("admin")
        if not admin:return
        data=self.body(20_000);visibility=str(data.get("visibility","private"))
        if visibility not in {"private","public"}:raise ValueError("Invalid template visibility")
        now=int(time.time()*1000);published_at=now if visibility=="public" else None
        with connect() as db:changed=db.execute("UPDATE user_templates SET visibility=?,published_at=?,updated_at=? WHERE id=?",(visibility,published_at,now,template_id)).rowcount
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
        with connect() as db:row=db.execute("SELECT id,email FROM users WHERE email=?",(email,)).fetchone()
        if row:
            token=self._create_auth_token(row["id"],"password-reset",30*60*1000);url=auth_action_url("/reset.html",token)
            try:sent=send_platform_email(row["email"],"Reset your E-invitation-website password",f"A password reset was requested for your E-invitation-website account.\n\nOpen this link within 30 minutes:\n{url}\n\nIf you did not request this, you can ignore this message.")
            except Exception as exc:print(f"Password-reset email delivery failed: {exc}",flush=True)
            if platform_env("EINVITE_DEV_AUTH_TOKENS","").lower() in {"1","true","yes"}:dev_token=token
        payload={"accepted":True,"sent":bool(sent)}
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
            salt=secrets.token_hex(16);db.execute("UPDATE users SET password_hash=?,salt=? WHERE id=?",(password_hash(new,salt),salt,row["user_id"]));db.execute("DELETE FROM sessions WHERE user_id=?",(row["user_id"],));db.execute("DELETE FROM auth_tokens WHERE user_id=? AND kind='password-reset'",(row["user_id"],))
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
            db.execute("UPDATE users SET email_verified=1 WHERE id=?",(row["user_id"],));db.execute("DELETE FROM auth_tokens WHERE user_id=? AND kind='email-verification'",(row["user_id"],))
        self.json(200,{"verified":True})

    def change_password(self):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);current=str(data.get("currentPassword",""));new=str(data.get("newPassword",""))
        if len(new)<8 or len(new)>200:raise ValueError("New password must be 8 to 200 characters")
        current_token=self.auth_token();current_token_hash=hashlib.sha256(current_token.encode()).hexdigest() if current_token else ""
        with connect() as db:
            row=db.execute("SELECT password_hash,salt FROM users WHERE id=?",(user["id"],)).fetchone()
            if not row or not hmac.compare_digest(row["password_hash"],password_hash(current,row["salt"])):return self.json(401,{"error":"Current password is incorrect"})
            salt=secrets.token_hex(16);db.execute("UPDATE users SET password_hash=?,salt=? WHERE id=?",(password_hash(new,salt),salt,user["id"]))
            if current_token_hash:db.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?",(user["id"],current_token_hash))
        self.json(200,{"changed":True})

    def plan_usage(self, db, user):
        plan=user["plan"] if user["plan"] in PLAN_LIMITS else "free"
        invitations=db.execute("SELECT COUNT(*) c FROM invitations WHERE owner_id=? AND archived=0",(user["id"],)).fetchone()["c"]
        templates=db.execute("SELECT COUNT(*) c FROM user_templates WHERE owner_id=?",(user["id"],)).fetchone()["c"]
        storage=db.execute("SELECT COALESCE(SUM(a.size),0) total FROM assets a JOIN invitations i ON i.id=a.invitation_id WHERE i.owner_id=?",(user["id"],)).fetchone()["total"]
        return plan,{"invitations":int(invitations or 0),"templates":int(templates or 0),"storageBytes":int(storage or 0)},PLAN_LIMITS[plan]

    def require_plan_capacity(self, user, kind, additional=1):
        if not PLAN_LIMITS_ENFORCED:return True
        with connect() as db:plan,usage,limits=self.plan_usage(db,user)
        if usage[kind]+additional>limits[kind]:
            label={"invitations":"active invitation","templates":"reusable template","storageBytes":"material storage"}.get(kind,kind)
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
        for collection,key in ((invitations,"draft_json"),(publications,"document_json"),(templates,"document_json"),(page_templates,"page_json"),(components,"payload_json")):
            for item in collection:
                if key in item:
                    try:item[key[:-5] if key.endswith('_json') else key]=json.loads(item.pop(key))
                    except Exception:pass
        for item in rsvps:
            try:item["answers"]=json.loads(item.pop("answers_json","{}") or "{}")
            except Exception:item["answers"]={}
        self.json(200,{"exportedAt":int(time.time()*1000),"account":{"id":user["id"],"email":user["email"],"role":user["role"],"plan":user["plan"],"emailVerified":bool(user["email_verified"])},"invitations":invitations,"publications":publications,"rsvps":rsvps,"guests":guests,"wishes":wishes,"assets":assets,"templates":templates,"pageTemplates":page_templates,"components":components})

    def register(self):
        if not self.rate_limit(f"register:{self.client_address[0]}",10,600): return
        data=self.body(100_000); email=str(data.get("email","")).strip().lower()[:254]; password=str(data.get("password",""))
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):raise ValueError("Valid email required")
        if len(password)<8:raise ValueError("Password must be at least 8 characters")
        user_id=str(uuid.uuid4()); salt=secrets.token_hex(16); now=int(time.time()*1000);admin_email=platform_env("EINVITE_ADMIN_EMAIL","").strip().lower();role="admin" if admin_email and email==admin_email else "customer"
        try:
            with connect() as db: db.execute("INSERT INTO users(id,email,password_hash,salt,created_at,role,email_verified,plan) VALUES(?,?,?,?,?,?,0,?)",(user_id,email,password_hash(password,salt),salt,now,role,"studio" if role=="admin" else "free"))
        except Exception as exc:
            if isinstance(exc,sqlite3.IntegrityError) or exc.__class__.__name__ in {"UniqueViolation","IntegrityError"}:return self.json(409,{"error":"An account with this email already exists"})
            raise
        self.create_session(user_id,email,role)
    def login(self):
        if not self.rate_limit(f"login:{self.client_address[0]}",30,600): return
        data=self.body(100_000); email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
        with connect() as db: row=db.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if not row or not hmac.compare_digest(row["password_hash"],password_hash(password,row["salt"])):return self.json(401,{"error":"Incorrect email or password"})
        self.create_session(row["id"],row["email"],row["role"] if "role" in row.keys() else "customer",bool(row["email_verified"] if "email_verified" in row.keys() else 0))
    def create_session(self,user_id,email,role="customer",email_verified=False):
        token=secrets.token_urlsafe(32); now=int(time.time()*1000); expires=now+30*24*60*60*1000
        with connect() as db:
            row=db.execute("SELECT email_verified,plan FROM users WHERE id=?",(user_id,)).fetchone()
            if email_verified is False:email_verified=bool(row["email_verified"]) if row else False
            plan=row["plan"] if row and "plan" in row.keys() else "free"
            db.execute("INSERT INTO sessions VALUES(?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),user_id,expires,now))
        cookie=f"{SESSION_COOKIE_NAME}={token}; Path=/; Max-Age={30*24*60*60}; HttpOnly; SameSite=Lax"
        if COOKIE_SECURE:cookie+="; Secure"
        # Token remains in the response for compatibility with the local/offline client and existing API tests.
        # Production clients can rely exclusively on the HttpOnly cookie.
        self.json(201,{"token":token,"user":{"id":user_id,"email":email,"role":role,"emailVerified":bool(email_verified),"plan":plan},"expiresAt":expires},{"Set-Cookie":cookie})
    def logout(self):
        tokens=self.auth_tokens()
        if tokens:
            with connect() as db:
                for token in tokens:db.execute("DELETE FROM sessions WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))
        cookie=f"{SESSION_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if COOKIE_SECURE:cookie+="; Secure"
        self.json(200,{"signedOut":True},{"Set-Cookie":cookie})
    def list_invitations(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            rows=db.execute("SELECT i.id,i.slug,i.updated_at,i.archived,i.views,i.access_mode,i.is_published,CASE WHEN i.is_published=1 THEN 'Published' ELSE 'Draft' END status,(SELECT COUNT(*) FROM rsvps r WHERE r.invitation_id=i.id) rsvps,i.draft_json,i.owner_id,COALESCE((SELECT role FROM invitation_collaborators c WHERE c.invitation_id=i.id AND c.user_id=?),'owner') collaboration_role FROM invitations i WHERE i.owner_id=? OR EXISTS(SELECT 1 FROM invitation_collaborators c WHERE c.invitation_id=i.id AND c.user_id=?) ORDER BY i.archived,i.updated_at DESC",(user["id"],user["id"],user["id"])).fetchall()
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
            result.append({"id":row["id"],"slug":row["slug"],"title":draft.get("fields",{}).get("names","Untitled invitation"),"type":draft.get("eventType","Invitation"),"status":"Archived" if row["archived"] else row["status"],"archived":bool(row["archived"]),"views":row["views"],"rsvps":row["rsvps"],"accessMode":row["access_mode"] or "unlisted","updatedAt":row["updated_at"],"shared":row["owner_id"]!=user["id"],"collaborationRole":row["collaboration_role"],"preview":preview})
        self.json(200,result)
    def create_invitation(self):
        user=self.require_user()
        if not user:return
        if not self.require_plan_capacity(user,"invitations"):return
        data = self.body(); document=validate_document(data.get("document",{})); invite_id = str(uuid.uuid4()); slug = clean_slug(data.get("slug", "our-invitation")); now = int(time.time()*1000)
        with connect() as db:
            base=slug; n=2
            while db.execute("SELECT 1 FROM invitations WHERE slug=?",(slug,)).fetchone(): slug=f"{base}-{n}"; n+=1
            db.execute("INSERT INTO invitations(id,slug,draft_json,updated_at,owner_id) VALUES(?,?,?,?,?)",(invite_id,slug,json.dumps(document),now,user["id"]))
        self.json(201,{"id":invite_id,"slug":slug})
    def get_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_read_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT id,slug,draft_json,updated_at,archived,access_mode,is_published,owner_id FROM invitations WHERE id=?",(invite_id,)).fetchone()
            role=self.invitation_role(db,invite_id,user["id"])
        if not row:return self.json(404,{"error":"Invitation not found"})
        self.json(200,{"id":row["id"],"slug":row["slug"],"document":json.loads(row["draft_json"]),"updatedAt":row["updated_at"],"archived":bool(row["archived"]),"accessMode":row["access_mode"] or "unlisted","published":bool(row["is_published"]),"collaborationRole":role,"owner":row["owner_id"]==user["id"]})
    def archive_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(10_000); archived=1 if data.get("archived",True) else 0
        with connect() as db: changed=db.execute("UPDATE invitations SET archived=?,updated_at=? WHERE id=? AND owner_id=?",(archived,int(time.time()*1000),invite_id,user["id"])).rowcount
        self.json(200 if changed else 404,{"archived":bool(archived)})
    def update_slug(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(50_000);slug=clean_slug(data.get("slug",""))
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            if db.execute("SELECT 1 FROM invitations WHERE slug=? AND id<>?",(slug,invite_id)).fetchone():return self.json(409,{"error":"That public link is already in use"})
            db.execute("UPDATE invitations SET slug=?,updated_at=? WHERE id=? AND owner_id=?",(slug,int(time.time()*1000),invite_id,user["id"]))
        self.json(200,{"slug":slug,"url":f"/i/{slug}"})

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
                    if len(password)<4 or len(password)>120:raise ValueError("Invitation password must be 4 to 120 characters")
                    salt=secrets.token_hex(16);hashed=password_hash(password,salt)
                elif row["access_password_hash"]:
                    hashed=row["access_password_hash"];salt=row["access_password_salt"]
                else:raise ValueError("Set an invitation password before enabling password protection")
            db.execute("UPDATE invitations SET access_mode=?,access_password_hash=?,access_password_salt=?,updated_at=? WHERE id=? AND owner_id=?",(mode,hashed,salt,int(time.time()*1000),invite_id,user["id"]))
            db.execute("DELETE FROM access_tokens WHERE invitation_id=?",(invite_id,))
        self.json(200,{"accessMode":mode})

    def get_analytics(self,invite_id):
        user=self.require_user()
        if not user:return
        now=int(time.time()*1000);start=now-30*24*60*60*1000
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            invite=db.execute("SELECT views FROM invitations WHERE id=?",(invite_id,)).fetchone()
            rows=db.execute("SELECT viewed_at FROM view_events WHERE invitation_id=? AND viewed_at>=? ORDER BY viewed_at",(invite_id,start)).fetchall()
            rsvps=db.execute("SELECT status,guest_count,created_at FROM rsvps WHERE invitation_id=?",(invite_id,)).fetchall()
            guests=db.execute("SELECT checked_in FROM guests WHERE invitation_id=?",(invite_id,)).fetchall()
        by_day={}
        for row in rows:
            day=time.strftime('%Y-%m-%d',time.localtime(row["viewed_at"]/1000));by_day[day]=by_day.get(day,0)+1
        statuses={}
        for row in rsvps:statuses[row["status"]]=statuses.get(row["status"],0)+1
        self.json(200,{"totalViews":int(invite["views"] or 0),"views30Days":len(rows),"viewsByDay":by_day,"rsvpTotal":len(rsvps),"rsvpGuests":sum(int(r["guest_count"] or 0) for r in rsvps),"rsvpStatuses":statuses,"guestListTotal":len(guests),"checkedIn":sum(1 for g in guests if g["checked_in"])})

    def delete_invitation(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            asset_rows=db.execute("SELECT path FROM assets WHERE invitation_id=?",(invite_id,)).fetchall()
            db.execute("DELETE FROM rsvps WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM guest_messages WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM view_events WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM access_tokens WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM publications WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM assets WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM guests WHERE invitation_id=?",(invite_id,));db.execute("DELETE FROM invitations WHERE id=?",(invite_id,))
        for row in asset_rows:delete_stored_asset(row["path"])
        self.json(200,{"deleted":True})
    def save_draft(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(); document=validate_document(data.get("document",{})); now=int(time.time()*1000)
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Editing permission required"})
            changed=db.execute("UPDATE invitations SET draft_json=?,updated_at=? WHERE id=?",(json.dumps(document),now,invite_id)).rowcount
        self.json(200 if changed else 404,{"saved":bool(changed),"updatedAt":now})
    def publish(self, invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(); now=int(time.time()*1000); pub_id=str(uuid.uuid4())
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Publishing permission required"})
            row=db.execute("SELECT slug,draft_json FROM invitations WHERE id=?",(invite_id,)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            document=validate_document(data.get("document") or json.loads(row["draft_json"])); db.execute("INSERT INTO publications VALUES(?,?,?,?,?)",(pub_id,invite_id,now,json.dumps(document),now));db.execute("UPDATE invitations SET is_published=1,updated_at=? WHERE id=?",(now,invite_id))
        self.json(201,{"publicationId":pub_id,"version":now,"slug":row["slug"],"url":f"/i/{row['slug']}"})
    def unpublish(self, invite_id):
        user=self.require_user()
        if not user:return
        now=int(time.time()*1000)
        with connect() as db:changed=db.execute("UPDATE invitations SET is_published=0,updated_at=? WHERE id=? AND owner_id=?",(now,invite_id,user["id"])).rowcount
        self.json(200 if changed else 404,{"published":False,"savedVersionsPreserved":True})

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
                with connect() as db:row=db.execute("SELECT updated_at FROM invitations WHERE id=?",(invite_id,)).fetchone()
                if not row:break
                updated=int(row["updated_at"] or 0)
                if updated!=last:
                    payload=json.dumps({"updatedAt":updated},separators=(",",":"))
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
        self.json(200,{"userId":target["id"],"email":target["email"],"role":role})
    def delete_collaborator(self, invite_id, collaborator_user_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.can_manage_invitation(db,invite_id,user["id"]):return self.json(403,{"error":"Management permission required"})
            changed=db.execute("DELETE FROM invitation_collaborators WHERE invitation_id=? AND user_id=?",(invite_id,collaborator_user_id)).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def access_token_valid(self, db, invitation_id, token):
        if not token:return False
        token_hash=hashlib.sha256(str(token).encode()).hexdigest();now=int(time.time()*1000)
        return db.execute("SELECT 1 FROM access_tokens WHERE token_hash=? AND invitation_id=? AND expires_at>?",(token_hash,invitation_id,now)).fetchone() is not None

    def get_public(self, slug, guest_token=None, access_token=None):
        with connect() as db:
            row=db.execute("SELECT i.id,i.access_mode,p.id publication_id,p.version,p.document_json FROM invitations i JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? AND i.archived=0 AND i.is_published=1 ORDER BY p.published_at DESC LIMIT 1",(slug,)).fetchone()
            if not row:return self.json(404,{"error":"Published invitation not found"})
            if row["access_mode"]=="password" and not self.access_token_valid(db,row["id"],access_token):return self.json(403,{"error":"Password required","protected":True})
            db.execute("UPDATE invitations SET views=views+1 WHERE id=?",(row["id"],));db.execute("INSERT INTO view_events VALUES(?,?,?,?)",(str(uuid.uuid4()),row["id"],row["publication_id"],int(time.time()*1000)))
        guest=None
        if guest_token:
            with connect() as db: guest=db.execute("SELECT id,name FROM guests WHERE invitation_id=? AND token=?",(row["id"],guest_token)).fetchone()
        self.json(200,{"invitationId":row["id"],"publicationId":row["publication_id"],"version":row["version"],"document":json.loads(row["document_json"]),"guest":dict(guest) if guest else None})

    def unlock_public(self, slug):
        if not self.rate_limit(f"unlock:{self.client_address[0]}:{slug}",12,600):return
        data=self.body(50_000);password=str(data.get("password",""));now=int(time.time()*1000)
        with connect() as db:
            row=db.execute("SELECT id,access_mode,access_password_hash,access_password_salt FROM invitations WHERE slug=? AND archived=0",(slug,)).fetchone()
            if not row:return self.json(404,{"error":"Invitation not found"})
            if row["access_mode"]!="password":return self.json(200,{"accessToken":None})
            if not row["access_password_hash"] or not row["access_password_salt"] or not hmac.compare_digest(row["access_password_hash"],password_hash(password,row["access_password_salt"])):return self.json(401,{"error":"Incorrect invitation password"})
            token=secrets.token_urlsafe(24);expires=now+24*60*60*1000;db.execute("INSERT INTO access_tokens VALUES(?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),row["id"],expires,now))
        self.json(200,{"accessToken":token,"expiresAt":expires})

    def get_guests(self,invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT g.id,g.name,g.phone,g.token,g.created_at,g.checked_in,g.checked_in_at,(SELECT status FROM rsvps r WHERE r.invitation_id=g.invitation_id AND lower(r.name)=lower(g.name) ORDER BY created_at DESC LIMIT 1) rsvp_status FROM guests g WHERE g.invitation_id=? ORDER BY g.created_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(row) for row in rows])
    def add_guest(self,invite_id):
        user=self.require_user()
        if not user:return
        data=self.body(100_000);name=str(data.get("name","")).strip()[:120]
        if not name:raise ValueError("Guest name is required")
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            guest_id=str(uuid.uuid4());token=secrets.token_urlsafe(12);db.execute("INSERT INTO guests(id,invitation_id,name,phone,token,created_at) VALUES(?,?,?,?,?,?)",(guest_id,invite_id,name,str(data.get("phone","")).strip()[:40],token,int(time.time()*1000)))
        self.json(201,{"id":guest_id,"name":name,"token":token})
    def delete_guest(self,invite_id,guest_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            changed=db.execute("DELETE FROM guests WHERE id=? AND invitation_id=?",(guest_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})
    def check_in_guest(self,invite_id,guest_id):
        user=self.require_user()
        if not user:return
        data=self.body(10_000);checked=1 if data.get("checkedIn",True) else 0;checked_at=int(time.time()*1000) if checked else None
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            changed=db.execute("UPDATE guests SET checked_in=?,checked_in_at=? WHERE id=? AND invitation_id=?",(checked,checked_at,guest_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"checkedIn":bool(checked),"checkedInAt":checked_at})
    def public_action_publication(self, db, slug, access_token=None):
        row=db.execute("SELECT i.id invitation_id,i.access_mode,p.id publication_id,p.document_json FROM invitations i JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? AND i.is_published=1 AND i.archived=0 ORDER BY p.published_at DESC LIMIT 1",(slug,)).fetchone()
        if not row:
            self.json(404,{"error":"Published invitation not found"});return None
        if row["access_mode"]=="password" and not self.access_token_valid(db,row["invitation_id"],access_token):
            self.json(403,{"error":"Invitation access is required","protected":True});return None
        return row

    def submit_wish(self, slug):
        if not self.rate_limit(f"wish:{self.client_address[0]}:{slug}",10,60):return
        data=self.body(100_000);name=str(data.get("name","")).strip()[:120];message=str(data.get("message","")).strip()[:2000];access_token=data.get("accessToken")
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
        data=self.body(100_000);name=str(data.get("name","")).strip()[:120];access_token=data.get("accessToken")
        if not name:raise ValueError("Name is required")
        try:count=max(1,min(10,int(data.get("count",1))))
        except (TypeError,ValueError):raise ValueError("Invalid guest count")
        status=str(data.get("status","Maybe"))[:40]
        if status not in {"Yes, joyfully","Unable to attend","Maybe"}:raise ValueError("Invalid RSVP status")
        answers={k:str(v).strip()[:2000] for k,v in data.items() if str(k).startswith("custom_")}
        if len(answers)>20:raise ValueError("Too many RSVP custom answers")
        with connect() as db:
            pub=self.public_action_publication(db,slug,access_token)
            if not pub:return
            document=json.loads(pub["document_json"])
            if document.get("settings",{}).get("rsvpEnabled") is False:return self.json(403,{"error":"RSVP is not enabled for this invitation"})
            for field in document.get("rsvpFields",[]) or []:
                key="custom_"+re.sub(r"[^A-Za-z0-9_-]","",str(field.get("id","")))
                value=answers.get(key,"")
                if field.get("required") and not value:raise ValueError(f"Required RSVP field is missing: {field.get('label','Question')}")
                if value and field.get("type")=="select" and value not in (field.get("options") or []):raise ValueError("Invalid RSVP option")
                if value and field.get("type")=="number":
                    try:float(value)
                    except ValueError:raise ValueError("Invalid numeric RSVP answer")
            rid=str(uuid.uuid4()); db.execute("INSERT INTO rsvps(id,invitation_id,publication_id,name,status,guest_count,note,created_at,answers_json) VALUES(?,?,?,?,?,?,?,?,?)",(rid,pub["invitation_id"],pub["publication_id"],name,status,count,str(data.get("note",""))[:1000],int(time.time()*1000),json.dumps(answers,ensure_ascii=False)))
        self.json(201,{"id":rid,"saved":True})

    def get_rsvps(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
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
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            changed=db.execute("UPDATE rsvps SET status=?,guest_count=? WHERE id=? AND invitation_id=?",(status,count,rsvp_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"updated":bool(changed),"status":status,"guestCount":count})

    def delete_rsvp(self,invite_id,rsvp_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            changed=db.execute("DELETE FROM rsvps WHERE id=? AND invitation_id=?",(rsvp_id,invite_id)).rowcount
        self.json(200 if changed else 404,{"deleted":bool(changed)})

    def get_versions(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,version,published_at FROM publications WHERE invitation_id=? ORDER BY published_at DESC",(invite_id,)).fetchall()
        self.json(200,[dict(r) for r in rows])

    def template_payload(self, row, include_document=True):
        value={
            "id":row["id"],"name":row["name"],"category":row["category"],
            "description":row["description"] or "","tags":json.loads(row["tags_json"] or "[]"),
            "favorite":bool(row["favorite"]),"currentVersion":int(row["current_version"] or 1),
            "thumbnail":json.loads(row["thumbnail_json"] or "{}"),
            "visibility":row["visibility"] if "visibility" in row.keys() else "private",
            "publishedAt":row["published_at"] if "published_at" in row.keys() else None,
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
        return name,category,description,json.dumps(tags,ensure_ascii=False),favorite,json.dumps(thumbnail,ensure_ascii=False)

    def list_marketplace_templates(self):
        with connect() as db:
            rows=db.execute("SELECT * FROM user_templates WHERE visibility='public' ORDER BY published_at DESC,updated_at DESC LIMIT 300").fetchall()
        self.json(200,[self.template_payload(r) for r in rows])

    def get_marketplace_template(self,template_id):
        with connect() as db:row=db.execute("SELECT * FROM user_templates WHERE id=? AND visibility='public'",(template_id,)).fetchone()
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
        name,category,description,tags_json,favorite,thumbnail_json=self.template_metadata(data)
        with connect() as db:
            visibility=str(data.get("visibility","private"));visibility=visibility if visibility in {"private","public"} else "private";published_at=now if visibility=="public" else None
            db.execute("INSERT INTO user_templates(id,owner_id,name,category,document_json,created_at,updated_at,description,tags_json,favorite,current_version,thumbnail_json,visibility,published_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(template_id,user["id"],name,category,json.dumps(document),now,now,description,tags_json,favorite,1,thumbnail_json,visibility,published_at))
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
            name,category,description,tags_json,favorite,thumbnail_json=self.template_metadata(data,existing)
            visibility=str(data.get("visibility",existing["visibility"] if "visibility" in existing.keys() else "private"))
            if visibility not in {"private","public"}:raise ValueError("Invalid template visibility")
            published_at=existing["published_at"] if "published_at" in existing.keys() else None
            if visibility=="public" and not published_at:published_at=now
            if visibility=="private":published_at=None
            document_json=existing["document_json"];current_version=int(existing["current_version"] or 1)
            if "document" in data:
                document=validate_document(data["document"]);document_json=json.dumps(document);current_version+=1
                db.execute("INSERT INTO template_versions(id,template_id,version,document_json,created_at) VALUES(?,?,?,?,?)",(str(uuid.uuid4()),template_id,current_version,document_json,now))
            db.execute("UPDATE user_templates SET name=?,category=?,description=?,tags_json=?,favorite=?,thumbnail_json=?,document_json=?,current_version=?,visibility=?,published_at=?,updated_at=? WHERE id=? AND owner_id=?",(name,category,description,tags_json,favorite,thumbnail_json,document_json,current_version,visibility,published_at,now,template_id,user["id"]))
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
            db.execute("INSERT INTO user_templates(id,owner_id,name,category,document_json,created_at,updated_at,description,tags_json,favorite,current_version,thumbnail_json,visibility,published_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(new_id,user["id"],data["name"],data["category"],json.dumps(document),now,now,data["description"],json.dumps(data["tags"],ensure_ascii=False),0,1,json.dumps(data["thumbnail"],ensure_ascii=False),"private",None))
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

    def get_account_assets(self):
        user=self.require_user()
        if not user:return
        with connect() as db:
            rows=db.execute("""SELECT a.id,a.invitation_id,a.name,a.mime,a.path,a.size,a.created_at,a.folder,a.tags_json,a.favorite,a.sha256,i.slug
                               FROM assets a JOIN invitations i ON i.id=a.invitation_id
                               WHERE i.owner_id=? ORDER BY a.favorite DESC,a.created_at DESC LIMIT 1000""",(user["id"],)).fetchall()
        result=[]
        with connect() as db:
            draft_rows=db.execute("SELECT draft_json FROM invitations WHERE owner_id=?",(user["id"],)).fetchall()
            published_rows=db.execute("SELECT p.document_json FROM publications p JOIN invitations i ON i.id=p.invitation_id WHERE i.owner_id=?",(user["id"],)).fetchall()
        searchable="\n".join(str(x["draft_json"] or "") for x in draft_rows)+"\n"+"\n".join(str(x["document_json"] or "") for x in published_rows)
        for r in rows:
            try: tags=json.loads(r["tags_json"] or "[]")
            except Exception: tags=[]
            url=asset_public_url(r['path']);usage_count=searchable.count(url)
            result.append({"id":r["id"],"invitationId":r["invitation_id"],"invitationSlug":r["slug"],"name":r["name"],"mime":r["mime"],"url":url,"size":r["size"],"createdAt":r["created_at"],"folder":r["folder"],"tags":tags,"favorite":bool(r["favorite"]),"sha256":r["sha256"],"usageCount":usage_count})
        self.json(200,result)

    def get_assets(self, invite_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            rows=db.execute("SELECT id,name,mime,path,size,created_at,folder,tags_json,favorite FROM assets WHERE invitation_id=? ORDER BY favorite DESC,created_at DESC",(invite_id,)).fetchall()
        result=[]
        for r in rows:
            try: tags=json.loads(r["tags_json"] or "[]")
            except Exception: tags=[]
            result.append({"id":r["id"],"name":r["name"],"mime":r["mime"],"url":asset_public_url(r['path']),"size":r["size"],"createdAt":r["created_at"],"folder":r["folder"],"tags":tags,"favorite":bool(r["favorite"])})
        self.json(200,result)
    def update_asset(self, asset_id):
        user=self.require_user()
        if not user:return
        data=self.body(30_000);name=str(data.get("name","")).strip()[:180];folder=str(data.get("folder","")).strip()[:80];tags=data.get("tags",[]);favorite=1 if data.get("favorite") else 0
        if not name:raise ValueError("Material name is required")
        if not isinstance(tags,list) or len(tags)>30:raise ValueError("Invalid material tags")
        tags=[str(x).strip()[:60] for x in tags if str(x).strip()][:30]
        with connect() as db:
            row=db.execute("SELECT a.id FROM assets a JOIN invitations i ON i.id=a.invitation_id WHERE a.id=? AND i.owner_id=?",(asset_id,user["id"])).fetchone()
            if not row:return self.json(404,{"error":"Material not found"})
            db.execute("UPDATE assets SET name=?,folder=?,tags_json=?,favorite=? WHERE id=?",(name,folder,json.dumps(tags,ensure_ascii=False),favorite,asset_id))
        self.json(200,{"id":asset_id,"name":name,"folder":folder,"tags":tags,"favorite":bool(favorite)})

    def delete_asset(self, invite_id, asset_id):
        user=self.require_user()
        if not user:return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
            row=db.execute("SELECT path FROM assets WHERE id=? AND invitation_id=?",(asset_id,invite_id)).fetchone()
            if not row:return self.json(404,{"error":"Material not found"})
            db.execute("DELETE FROM assets WHERE id=? AND invitation_id=?",(asset_id,invite_id))
            still_used=db.execute("SELECT 1 FROM assets WHERE path=? LIMIT 1",(row["path"],)).fetchone()
        if not still_used:delete_stored_asset(row["path"])
        self.json(200,{"deleted":True})
    def _upload_claim(self, invite_id, asset_id, path, mime, size, expires):
        payload=f"{invite_id}|{asset_id}|{path}|{mime}|{int(size)}|{int(expires)}"
        signature=hmac.new(UPLOAD_SIGNING_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
        return {"assetId":asset_id,"path":path,"mime":mime,"size":int(size),"expires":int(expires),"signature":signature}
    def _verify_upload_claim(self, invite_id, claim):
        try:
            asset_id=str(claim.get("assetId",""));path=Path(str(claim.get("path",""))).name;mime=str(claim.get("mime",""));size=int(claim.get("size",0));expires=int(claim.get("expires",0));signature=str(claim.get("signature",""))
        except Exception:raise ValueError("Invalid upload claim")
        expected=self._upload_claim(invite_id,asset_id,path,mime,size,expires)["signature"]
        if expires<int(time.time()) or not hmac.compare_digest(signature,expected):raise ValueError("Upload claim expired or invalid")
        if not asset_id or not path.startswith(asset_id):raise ValueError("Invalid upload path")
        return asset_id,path,mime,size
    def presign_asset_upload(self, invite_id):
        user=self.require_user()
        if not user:return
        if not object_storage_enabled():return self.json(409,{"error":"Direct object-storage upload is not configured","directUpload":False})
        if not self.rate_limit(f"upload-presign:{user['id']}:{invite_id}",120,3600):return
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        data=self.body(50_000);name=str(data.get("name","upload"))[:180] or "upload";mime=str(data.get("mime","application/octet-stream")).lower();size=int(data.get("size",0) or 0)
        allowed={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/gif":".gif","audio/mpeg":".mp3","audio/mp4":".m4a","video/mp4":".mp4","video/webm":".webm"}
        if mime not in allowed:raise ValueError("Unsupported material type")
        limit=50_000_000 if mime.startswith("video/") else 15_000_000
        if size<=0 or size>limit:raise ValueError(f"Material exceeds {limit//1_000_000} MB or is empty")
        if not self.require_plan_capacity(user,"storageBytes",size):return
        asset_id=str(uuid.uuid4());path=asset_id+allowed[mime];expires=int(time.time())+15*60;claim=self._upload_claim(invite_id,asset_id,path,mime,size,expires)
        upload_url=object_storage_client().generate_presigned_url("put_object",Params={"Bucket":OBJECT_STORAGE_BUCKET,"Key":object_storage_key(path),"ContentType":mime},ExpiresIn=15*60,HttpMethod="PUT")
        self.json(200,{"directUpload":True,"uploadUrl":upload_url,"headers":{"Content-Type":mime},"name":name,"claim":claim,"url":asset_public_url(path)})
    def complete_presigned_asset(self, invite_id):
        user=self.require_user()
        if not user:return
        if not object_storage_enabled():return self.json(409,{"error":"Direct object-storage upload is not configured"})
        with connect() as db:
            if not self.can_edit_invitation(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        data=self.body(80_000);claim=data.get("claim") if isinstance(data.get("claim"),dict) else {};asset_id,path,mime,expected_size=self._verify_upload_claim(invite_id,claim);name=str(data.get("name","upload"))[:180] or "upload"
        head=object_storage_client().head_object(Bucket=OBJECT_STORAGE_BUCKET,Key=object_storage_key(path));actual_size=int(head.get("ContentLength",0) or 0)
        if actual_size!=expected_size:raise ValueError("Uploaded material size does not match the signed request")
        first=object_storage_client().get_object(Bucket=OBJECT_STORAGE_BUCKET,Key=object_storage_key(path),Range="bytes=0-31")["Body"].read()
        validate_material_bytes(first,mime)
        with connect() as db:db.execute("INSERT INTO assets(id,invitation_id,name,mime,path,size,created_at,folder,tags_json,favorite,sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(asset_id,invite_id,name,mime,path,actual_size,int(time.time()*1000),"","[]",0,""))
        self.json(201,{"id":asset_id,"url":asset_public_url(path),"size":actual_size,"directUpload":True})

    def upload_raw(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.rate_limit(f"upload:{user['id']}:{invite_id}",60,3600): return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        mime=str(self.headers.get("Content-Type","application/octet-stream")).split(";",1)[0].strip().lower();allowed={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/gif":".gif","audio/mpeg":".mp3","audio/mp4":".m4a","video/mp4":".mp4","video/webm":".webm"}
        if mime not in allowed:raise ValueError("Unsupported material type")
        limit=50_000_000 if mime.startswith("video/") else 15_000_000;size=int(self.headers.get("Content-Length","0") or 0)
        if size<=0:raise ValueError("Empty material upload")
        if size>limit:raise ValueError(f"Material exceeds {limit//1_000_000} MB")
        if not self.require_plan_capacity(user,"storageBytes",size):return
        raw=self.rfile.read(size)
        if len(raw)!=size:raise ValueError("Material upload was incomplete")
        validate_material_bytes(raw,mime)
        name=unquote(str(self.headers.get("X-File-Name","upload")))[:180] or "upload";aid=str(uuid.uuid4());digest=hashlib.sha256(raw).hexdigest();duplicate=False
        with connect() as db:
            existing=db.execute("SELECT a.path FROM assets a JOIN invitations i ON i.id=a.invitation_id WHERE i.owner_id=? AND a.sha256=? AND a.size=? LIMIT 1",(user["id"],digest,len(raw))).fetchone()
        if existing:filename=existing["path"];duplicate=True
        else:filename=aid+allowed[mime];store_asset_bytes(filename,raw,mime)
        with connect() as db:db.execute("INSERT INTO assets(id,invitation_id,name,mime,path,size,created_at,folder,tags_json,favorite,sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(aid,invite_id,name,mime,filename,len(raw),int(time.time()*1000),"","[]",0,digest))
        self.json(201,{"id":aid,"url":asset_public_url(filename),"size":len(raw),"duplicate":duplicate})

    def upload(self, invite_id):
        user=self.require_user()
        if not user:return
        if not self.rate_limit(f"upload:{user['id']}:{invite_id}",60,3600): return
        with connect() as db:
            if not self.owns(db,invite_id,user["id"]):return self.json(404,{"error":"Invitation not found"})
        data=self.body(80_000_000); raw=base64.b64decode(data["base64"],validate=True); mime=str(data.get("mime","application/octet-stream")); allowed={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/gif":".gif","audio/mpeg":".mp3","audio/mp4":".m4a","video/mp4":".mp4","video/webm":".webm"}
        if mime not in allowed:raise ValueError("Unsupported material type")
        limit=50_000_000 if mime.startswith("video/") else 15_000_000
        if len(raw)>limit:raise ValueError(f"Material exceeds {limit//1_000_000} MB")
        if not self.require_plan_capacity(user,"storageBytes",len(raw)):return
        validate_material_bytes(raw,mime)
        aid=str(uuid.uuid4());digest=hashlib.sha256(raw).hexdigest();duplicate=False
        with connect() as db:existing=db.execute("SELECT a.path FROM assets a JOIN invitations i ON i.id=a.invitation_id WHERE i.owner_id=? AND a.sha256=? AND a.size=? LIMIT 1",(user["id"],digest,len(raw))).fetchone()
        if existing:filename=existing["path"];duplicate=True
        else:filename=aid+allowed[mime];store_asset_bytes(filename,raw,mime)
        with connect() as db: db.execute("INSERT INTO assets(id,invitation_id,name,mime,path,size,created_at,folder,tags_json,favorite,sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(aid,invite_id,str(data.get("name","upload"))[:180],mime,filename,len(raw),int(time.time()*1000),"","[]",0,digest))
        self.json(201,{"id":aid,"url":asset_public_url(filename),"size":len(raw),"duplicate":duplicate})
    def serve_asset(self, path):
        clean=Path(str(path or "")).name
        if not clean:return self.json(404,{"error":"Material not found"})
        if object_storage_enabled():
            try:
                response=object_storage_client().get_object(Bucket=OBJECT_STORAGE_BUCKET,Key=object_storage_key(clean));body=response["Body"].read();content_type=response.get("ContentType") or mimetypes.guess_type(clean)[0] or "application/octet-stream"
            except Exception:return self.json(404,{"error":"Material not found"})
        else:
            local=UPLOADS/clean
            if not local.is_file():return self.json(404,{"error":"Material not found"})
            body=local.read_bytes();content_type=mimetypes.guess_type(clean)[0] or "application/octet-stream"
        self.send_response(200);self.send_header("Content-Type",content_type);self.send_header("Cache-Control","public,max-age=31536000,immutable");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

    def serve_public(self, slug):
        title="Invitation";description="You are invited to a special event."
        with connect() as db:
            row=db.execute("SELECT i.access_mode,p.document_json FROM invitations i LEFT JOIN publications p ON p.invitation_id=i.id WHERE i.slug=? AND i.is_published=1 AND i.archived=0 ORDER BY p.published_at DESC LIMIT 1",(slug,)).fetchone()
            if row and row["access_mode"]!="password" and row["document_json"]:
                try:
                    document=json.loads(row["document_json"]);fields=document.get("fields",{});title=str(fields.get("names") or "Invitation")[:120];description=str(fields.get("message") or "You are invited to a special event.")[:240]
                except Exception:pass
            elif row and row["access_mode"]=="password":title="Private Invitation";description="A private invitation is waiting for you."
        page=(ROOT/"public.html").read_text(encoding="utf-8").replace("__INVITATION_SLUG__",slug).replace("__INVITATION_TITLE__",html.escape(title,quote=True)).replace("__INVITATION_DESCRIPTION__",html.escape(description,quote=True))
        body=page.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Cache-Control","no-cache"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the E-invitation-website development server.")
    parser.add_argument("--host", default=os.environ.get("HOST","127.0.0.1"), help="Bind host (default: 127.0.0.1; use 0.0.0.0 for deployment)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT","4175")), help="HTTP port (default: 4175 or PORT environment variable)")
    args = parser.parse_args()
    display_host="127.0.0.1" if args.host in {"0.0.0.0","::"} else args.host
    address = f"http://{display_host}:{args.port}"
    print(f"E-invitation-website: {address}", flush=True)
    print(f"Data directory: {DATA}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
