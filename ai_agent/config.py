from dataclasses import dataclass
import os
import json


def _env(name: str, default: str = "") -> str:
    legacy = name.replace("EINVITE_", "SOVAN_", 1)
    return os.environ.get(name, os.environ.get(legacy, default))


def _bool(name: str, default: bool = False) -> bool:
    return _env(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(_env(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class AgentConfig:
    endpoint: str
    api_key: str
    model: str
    provider: str
    timeout_seconds: int
    max_context_bytes: int
    max_provider_bytes: int
    max_tool_calls: int
    max_actions_per_job: int
    max_concurrent_jobs: int
    retention_days_default: int
    enabled_default: bool
    fake_provider_enabled: bool
    allow_external_provider: bool
    provider_routes: tuple[dict, ...] = ()
    local_provider_specs: tuple[dict, ...] = ()
    local_provider_allowlist: tuple[str, ...] = ()
    local_model_roles: dict[str, str] | None = None
    local_provider_timeout_seconds: int = 5
    local_provider_concurrency: int = 1
    local_model_dir: str = ""

    @classmethod
    def from_environment(cls) -> "AgentConfig":
        endpoint = _env("EINVITE_AI_ENDPOINT", "").strip()
        provider = _env("EINVITE_AI_PROVIDER", "external" if endpoint else "offline").strip().lower() or "offline"
        raw_routes = _env("EINVITE_AI_PROVIDER_ROUTES_JSON", "").strip()
        routes = []
        if raw_routes:
            try:
                parsed = json.loads(raw_routes)
                if isinstance(parsed, list):
                    for item in parsed[:8]:
                        if not isinstance(item, dict):
                            continue
                        route_endpoint = str(item.get("endpoint") or "").strip()
                        if not route_endpoint:
                            continue
                        routes.append({
                            "id": str(item.get("id") or f"route-{len(routes)+1}")[:80],
                            "endpoint": route_endpoint,
                            "apiKey": str(item.get("apiKey") or ""),
                            "model": str(item.get("model") or ""),
                            "priority": max(0, min(1000, int(item.get("priority") or len(routes)))),
                        })
            except Exception:
                routes = []
        routes.sort(key=lambda item: item["priority"])
        local_specs = []
        raw_local = _env("EINVITE_LOCAL_AI_PROVIDERS_JSON", "").strip()
        local_enabled = _bool("EINVITE_LOCAL_AI_ENABLED", False)
        if raw_local:
            try:
                parsed = json.loads(raw_local)
                if isinstance(parsed, list):
                    for item in parsed[:12]:
                        if isinstance(item, dict) and str(item.get("endpoint") or "").strip():
                            local_specs.append({
                                "id": str(item.get("id") or f"local-{len(local_specs)+1}")[:80],
                                "label": str(item.get("label") or item.get("id") or "Local model")[:100],
                                "kind": str(item.get("kind") or "openai")[:30],
                                "endpoint": str(item.get("endpoint") or "").strip(),
                                "enabled": item.get("enabled", True) is not False,
                            })
            except Exception:
                local_specs = []
        elif local_enabled:
            local_specs = [
                {"id":"ollama","label":"Ollama","kind":"ollama","endpoint":"http://127.0.0.1:11434","enabled":True},
                {"id":"lmstudio","label":"LM Studio","kind":"openai","endpoint":"http://127.0.0.1:1234","enabled":True},
                {"id":"gpt4all","label":"GPT4All","kind":"openai","endpoint":"http://127.0.0.1:4891","enabled":True},
            ]
        allowlist = tuple(x.strip().rstrip("/") for x in _env("EINVITE_LOCAL_AI_ALLOWLIST", "").split(",") if x.strip())
        model_roles = {}
        try:
            parsed_roles = json.loads(_env("EINVITE_AI_MODEL_ROLES_JSON", "{}") or "{}")
            if isinstance(parsed_roles, dict):
                model_roles = {str(k)[:40]: str(v)[:300] for k, v in parsed_roles.items() if isinstance(v, (str, int, float))}
        except Exception:
            model_roles = {}
        return cls(
            endpoint=endpoint,
            api_key=_env("EINVITE_AI_API_KEY", "").strip(),
            model=_env("EINVITE_AI_MODEL", "").strip(),
            provider=provider,
            timeout_seconds=_int("EINVITE_AI_TIMEOUT", 20, 2, 60),
            max_context_bytes=_int("EINVITE_AI_MAX_CONTEXT_BYTES", 180_000, 20_000, 500_000),
            max_provider_bytes=_int("EINVITE_AI_MAX_PROVIDER_BYTES", 2_000_000, 50_000, 5_000_000),
            max_tool_calls=_int("EINVITE_AI_MAX_TOOL_CALLS", 40, 1, 100),
            max_actions_per_job=_int("EINVITE_AI_MAX_ACTIONS_PER_JOB", 80, 1, 200),
            max_concurrent_jobs=_int("EINVITE_AI_MAX_CONCURRENT_JOBS", 2, 1, 8),
            retention_days_default=_int("EINVITE_AI_RETENTION_DAYS", 30, 0, 3650),
            enabled_default=_bool("EINVITE_AI_ENABLED", True),
            fake_provider_enabled=_bool("EINVITE_AI_FAKE_PROVIDER", provider == "fake"),
            allow_external_provider=_bool("EINVITE_AI_ALLOW_EXTERNAL_PROVIDER", bool(endpoint or routes)),
            provider_routes=tuple(routes),
            local_provider_specs=tuple(local_specs),
            local_provider_allowlist=allowlist,
            local_model_roles=model_roles,
            local_provider_timeout_seconds=_int("EINVITE_LOCAL_AI_TIMEOUT", 5, 2, 60),
            local_provider_concurrency=_int("EINVITE_LOCAL_AI_CONCURRENCY", 1, 1, 8),
            local_model_dir=_env("EINVITE_LOCAL_MODEL_DIR", "").strip(),
        )

    @property
    def connected(self) -> bool:
        external = self.provider == "external" and self.allow_external_provider and bool(self.endpoint or self.provider_routes)
        local = self.provider == "local" and bool(self.local_provider_specs)
        return external or local

    @property
    def local_enabled(self) -> bool:
        return bool(self.local_provider_specs)

    @property
    def disclosure(self) -> str:
        if self.provider == "local" and self.local_provider_specs:
            return "Local AI provider configured on the server"
        if self.connected:
            return "Connected AI provider configured on the server"
        if self.fake_provider_enabled:
            return "Deterministic test provider — no external AI call"
        return "Template helper — offline"
