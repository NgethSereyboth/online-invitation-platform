"""Server-only local model discovery and governed provider adapters.

Local endpoints are never accepted from browser/user input. They come from process
configuration and are constrained by an exact allowlist plus loopback-safe defaults.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import ipaddress
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class LocalProviderError(RuntimeError):
    def __init__(self, message: str, code: str = "local_provider_error"):
        super().__init__(message)
        self.code = code


DEFAULT_LOCAL_PROVIDERS = (
    {"id": "ollama", "label": "Ollama", "kind": "ollama", "endpoint": "http://127.0.0.1:11434"},
    {"id": "lmstudio", "label": "LM Studio", "kind": "openai", "endpoint": "http://127.0.0.1:1234"},
    {"id": "gpt4all", "label": "GPT4All", "kind": "openai", "endpoint": "http://127.0.0.1:4891"},
)
MODEL_ROLES = ("general", "planning", "vision", "writing", "translation", "embedding")


class _NoProviderRedirects(urllib.request.HTTPRedirectHandler):
    """Fail closed instead of allowing a provider to redirect outside its approved origin."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - urllib hook signature
        return None


_PROVIDER_OPENER = urllib.request.build_opener(_NoProviderRedirects())


def _clean_endpoint(value: str) -> str:
    parsed = urllib.parse.urlsplit(str(value or "").strip().rstrip("/"))
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise LocalProviderError("Local provider endpoint must be an administrator-configured HTTP origin", "invalid_local_endpoint")
    if parsed.path not in {"", "/"}:
        raise LocalProviderError("Local provider endpoint must not contain a path", "invalid_local_endpoint")
    port = parsed.port
    host = parsed.hostname.lower()
    return f"http://{host}{f':{port}' if port else ''}"


def _is_loopback_host(host: str) -> bool:
    if host.lower() in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        try:
            return all(ipaddress.ip_address(item[4][0]).is_loopback for item in socket.getaddrinfo(host, None))
        except Exception:
            return False


def validate_endpoint(endpoint: str, allowlist: set[str]) -> str:
    clean = _clean_endpoint(endpoint)
    parsed = urllib.parse.urlsplit(clean)
    if clean not in allowlist and not _is_loopback_host(parsed.hostname or ""):
        raise LocalProviderError("Local provider endpoint is not on the administrator allowlist", "local_endpoint_not_allowed")
    return clean


def _json_request(url: str, timeout: int, method: str = "GET", payload: dict[str, Any] | None = None, maximum: int = 3_000_000) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "E-invitation-local-ai/53.1"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with _PROVIDER_OPENER.open(request, timeout=timeout) as response:
        raw = response.read(maximum + 1)
    if len(raw) > maximum:
        raise LocalProviderError("Local provider response exceeded the bounded size", "local_provider_response_too_large")
    try:
        return json.loads(raw or b"{}")
    except Exception as exc:
        raise LocalProviderError("Local provider returned invalid JSON", "malformed_local_provider_response") from exc


def _model_capabilities(provider_kind: str, model: dict[str, Any]) -> dict[str, Any]:
    name = str(model.get("id") or model.get("name") or model.get("model") or "")[:200]
    lower = name.lower()
    details = model.get("details") if isinstance(model.get("details"), dict) else {}
    families = " ".join(str(x) for x in (details.get("families") or []) if isinstance(x, str)).lower()
    text = f"{lower} {families} {json.dumps(details, ensure_ascii=False).lower()}"
    vision = any(token in text for token in ("vision", "llava", "minicpm-v", "qwen2-vl", "qwen-vl", "gemma3", "pixtral", "moondream"))
    embedding = any(token in text for token in ("embed", "embedding", "nomic-embed", "bge-", "e5-"))
    # Tool and structured output support cannot be proven by model name. Mark only
    # known modern families as likely and keep destructive routing server-governed.
    tool = any(token in text for token in ("qwen", "llama3", "llama-3", "mistral", "command-r", "gemma3", "phi-4", "gpt-oss")) and not embedding
    structured = tool or any(token in text for token in ("json", "instruct"))
    context = 0
    for key in ("context_length", "contextLength", "num_ctx", "max_context_length"):
        try:
            context = max(context, int(model.get(key) or details.get(key) or 0))
        except Exception:
            pass
    loaded = model.get("loaded")
    if loaded is None:
        loaded = model.get("status") not in {"unloaded", "not-loaded"}
    return {
        "id": name,
        "name": name,
        "type": "embedding" if embedding else ("vision" if vision else "text"),
        "toolCalling": bool(tool),
        "vision": bool(vision),
        "structuredOutput": bool(structured),
        "embedding": bool(embedding),
        "contextLength": context or None,
        "loaded": bool(loaded),
        "providerKind": provider_kind,
    }


def discover_model_directory(path_value: str, public_roots: tuple[str, ...] = ()) -> dict[str, Any]:
    """Discover model-file metadata only; never import or execute files."""
    raw = str(path_value or "").strip()
    if not raw:
        return {"configured": False, "available": False, "files": [], "requiresRuntimeRegistration": True}
    try:
        root = Path(raw).expanduser().resolve(strict=False)
        for value in public_roots:
            if not value:
                continue
            public = Path(value).expanduser().resolve(strict=False)
            if root == public or public in root.parents:
                return {"configured": True, "available": False, "files": [], "error": "model_directory_inside_public_root", "requiresRuntimeRegistration": True}
        if not root.is_dir():
            return {"configured": True, "available": False, "files": [], "error": "model_directory_unavailable", "requiresRuntimeRegistration": True}
        rows=[]
        allowed={".gguf", ".safetensors"}
        for item in root.iterdir():
            if len(rows) >= 200:
                break
            try:
                if item.is_symlink() or not item.is_file() or item.suffix.lower() not in allowed:
                    continue
                stat=item.stat()
                rows.append({"name":item.name[:240],"extension":item.suffix.lower(),"size":int(stat.st_size),"discoveredOnly":True})
            except OSError:
                continue
        rows.sort(key=lambda value:value["name"].lower())
        return {"configured": True, "available": True, "files": rows, "requiresRuntimeRegistration": True}
    except Exception:
        return {"configured": True, "available": False, "files": [], "error": "model_directory_invalid", "requiresRuntimeRegistration": True}


@dataclass(frozen=True)
class LocalProviderSpec:
    id: str
    label: str
    kind: str
    endpoint: str
    enabled: bool = True


class LocalProviderManager:
    def __init__(self, specs: tuple[dict[str, Any], ...] = (), allowlist: tuple[str, ...] = (), timeout: int = 5, concurrency: int = 1, model_roles: dict[str, Any] | None = None):
        configured = list(specs or ())
        self.allowlist = set()
        for item in allowlist or ():
            try:
                self.allowlist.add(_clean_endpoint(str(item)))
            except LocalProviderError:
                continue
        self.specs: list[LocalProviderSpec] = []
        for raw in configured:
            if not isinstance(raw, dict) or raw.get("enabled", True) is False:
                continue
            try:
                endpoint = validate_endpoint(str(raw.get("endpoint") or ""), self.allowlist)
            except LocalProviderError:
                continue
            provider_id = str(raw.get("id") or "local")[:80]
            kind = str(raw.get("kind") or "openai").lower()
            if kind not in {"ollama", "openai"}:
                continue
            self.specs.append(LocalProviderSpec(provider_id, str(raw.get("label") or provider_id)[:100], kind, endpoint, True))
        self.timeout = max(2, min(60, int(timeout or 5)))
        self.semaphore = threading.BoundedSemaphore(max(1, min(8, int(concurrency or 1))))
        self.model_roles = {role: str((model_roles or {}).get(role) or "")[:300] for role in MODEL_ROLES}
        self._cache: tuple[float, list[dict[str, Any]]] = (0.0, [])

    def _spec(self, provider_id: str) -> LocalProviderSpec:
        for spec in self.specs:
            if spec.id == provider_id:
                return spec
        raise LocalProviderError("Local provider is not configured", "local_provider_not_configured")

    def _discover_spec(self, spec: LocalProviderSpec) -> dict[str, Any]:
        started = time.time()
        candidates = ["/api/tags", "/v1/models"] if spec.kind == "ollama" else (["/api/v1/models", "/v1/models"] if spec.id == "lmstudio" else ["/v1/models"])
        last_error = ""
        payload: Any = None
        used = ""
        for path in candidates:
            try:
                payload = _json_request(spec.endpoint + path, self.timeout)
                used = path
                break
            except Exception as exc:
                last_error = getattr(exc, "code", type(exc).__name__)
        if payload is None:
            return {"id": spec.id, "label": spec.label, "kind": spec.kind, "endpointLabel": spec.endpoint, "healthy": False, "models": [], "error": last_error or "unavailable", "checkedAt": int(time.time() * 1000)}
        rows = []
        if isinstance(payload, dict):
            source = payload.get("models") or payload.get("data") or []
            if isinstance(source, list):
                rows = [item if isinstance(item, dict) else {"id": str(item)} for item in source[:300]]
        models = [_model_capabilities(spec.kind, item) for item in rows]
        return {
            "id": spec.id, "label": spec.label, "kind": spec.kind, "endpointLabel": spec.endpoint,
            "healthy": True, "models": models, "modelEndpoint": used,
            "latencyMs": int((time.time() - started) * 1000), "checkedAt": int(time.time() * 1000), "lastSuccessfulCheck": int(time.time() * 1000),
        }

    def catalog(self, force: bool = False) -> list[dict[str, Any]]:
        stamp, cached = self._cache
        if not force and cached and time.time() - stamp < 20:
            return json.loads(json.dumps(cached))
        result = [self._discover_spec(spec) for spec in self.specs]
        self._cache = (time.time(), result)
        return json.loads(json.dumps(result))

    def role_status(self) -> dict[str, Any]:
        catalog = self.catalog()
        index = {(provider["id"], model["id"]): model for provider in catalog for model in provider.get("models", [])}
        result = {}
        for role, selection in self.model_roles.items():
            provider_id, _, model_id = selection.partition(":")
            model = index.get((provider_id, model_id)) if provider_id and model_id else None
            result[role] = {"selection": selection, "available": bool(model), "capabilities": model or {}}
        return result

    def _role_selection(self, role: str) -> tuple[LocalProviderSpec, str, dict[str, Any]]:
        selection = self.model_roles.get(role) or self.model_roles.get("general") or ""
        provider_id, sep, model_id = selection.partition(":")
        if not sep or not provider_id or not model_id:
            raise LocalProviderError(f"No local model is selected for the {role} role", "local_model_not_selected")
        spec = self._spec(provider_id)
        catalog = self.catalog()
        model = next((model for provider in catalog if provider.get("id") == provider_id for model in provider.get("models", []) if model.get("id") == model_id), None)
        if not model:
            raise LocalProviderError("Selected local model is unavailable", "local_model_unavailable")
        return spec, model_id, model

    def generate(self, role: str, payload: dict[str, Any], require_tools: bool = False, require_vision: bool = False, require_structured: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
        spec, model_id, capabilities = self._role_selection(role)
        if require_tools and not capabilities.get("toolCalling"):
            raise LocalProviderError("Selected model is not approved for tool planning", "local_model_lacks_tools")
        if require_vision and not capabilities.get("vision"):
            raise LocalProviderError("Selected model does not advertise vision support", "local_model_lacks_vision")
        if require_structured and not capabilities.get("structuredOutput"):
            raise LocalProviderError("Selected model is not approved for structured output", "local_model_lacks_structured_output")
        if not self.semaphore.acquire(timeout=self.timeout):
            raise LocalProviderError("Local model concurrency limit was reached", "local_provider_busy")
        try:
            messages = json.loads(json.dumps(payload.get("messages") or []))
            images = [item for item in (payload.get("images") or []) if isinstance(item, dict) and item.get("base64")]
            if images and messages:
                if spec.kind == "ollama":
                    messages[-1]["images"] = [str(item.get("base64") or "") for item in images[:6]]
                else:
                    text = messages[-1].get("content") if isinstance(messages[-1], dict) else ""
                    parts = [{"type":"text","text":str(text or "")}]
                    for item in images[:6]:
                        mime=str(item.get("mime") or "image/jpeg")[:80]
                        parts.append({"type":"image_url","image_url":{"url":f"data:{mime};base64,{item.get('base64')}"}})
                    messages[-1]["content"] = parts
            if spec.kind == "ollama":
                request_payload = {
                    "model": model_id,
                    "messages": messages,
                    "stream": False,
                    "format": "json" if require_structured else None,
                    "options": payload.get("options") or {},
                }
                request_payload = {k: v for k, v in request_payload.items() if v is not None}
                raw = _json_request(spec.endpoint + "/api/chat", self.timeout, "POST", request_payload, maximum=5_000_000)
                content = ((raw or {}).get("message") or {}).get("content") if isinstance(raw, dict) else None
                result = {"content": str(content or ""), "raw": raw}
            else:
                request_payload = {"model": model_id, "messages": messages, "temperature": payload.get("temperature", 0.2), "stream": False}
                if require_structured:
                    request_payload["response_format"] = {"type": "json_object"}
                raw = _json_request(spec.endpoint + "/v1/chat/completions", self.timeout, "POST", request_payload, maximum=5_000_000)
                choices = raw.get("choices") if isinstance(raw, dict) else []
                content = (((choices or [{}])[0].get("message") or {}).get("content")) if isinstance(choices, list) and choices else ""
                result = {"content": str(content or ""), "raw": raw}
            return result, {"providerId": spec.id, "model": model_id, "capabilities": capabilities}
        except LocalProviderError:
            raise
        except Exception as exc:
            raise LocalProviderError("Local model request failed", "local_provider_unavailable") from exc
        finally:
            self.semaphore.release()
