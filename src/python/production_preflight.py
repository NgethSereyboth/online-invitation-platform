#!/usr/bin/env python3
"""Credential-safe production configuration validation.

The validator never prints secret values and performs no network access unless
``--check-dependencies`` is requested. The server also calls the same validator
at production startup so an incomplete deployment fails closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import ipaddress
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

TRUE_VALUES = {"1", "true", "yes", "on"}
PLACEHOLDER = re.compile(r"(?:change|replace|example|placeholder|your[-_ ]|secret-manager|password)", re.I)
SECRET_NAMES = (
    "EINVITE_UPLOAD_SIGNING_SECRET",
    "EINVITE_MEDIA_SIGNING_SECRET",
    "EINVITE_GUEST_TOKEN_SECRET",
)


def truthy(value: object) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def valid_exact_host(value: str) -> bool:
    host=str(value or "").strip().lower().rstrip(".")
    if not host or any(ch in host for ch in "/\\@?#"):
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        if ":" in host:return False
        label=r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        return host=="localhost" or bool(re.fullmatch(rf"{label}(?:\.{label})*",host))


def _valid_proxy_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(str(value or "").strip())
        return True
    except ValueError:
        return False


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"Invalid environment line {number}: expected NAME=value")
        name, value = line.split("=", 1)
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"Invalid environment variable name on line {number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[name] = value
    return values


def _url_error(value: str, schemes: set[str], label: str, *, root_only: bool = False) -> str:
    try:
        parsed = urlparse(value)
    except Exception:
        return f"{label} is not a valid URL."
    if parsed.scheme not in schemes or not parsed.hostname:
        return f"{label} must use {', '.join(sorted(schemes))} and include a host."
    if parsed.username and label == "EINVITE_PUBLIC_BASE_URL":
        return f"{label} must not contain embedded credentials."
    if root_only and (parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        return f"{label} must be an origin without a path, query, or fragment."
    return ""


def _secret_error(name: str, value: str) -> str:
    if len(value) < 32:
        return f"{name} must contain at least 32 characters."
    if PLACEHOLDER.search(value) or len(set(value)) < 8:
        return f"{name} appears to be a placeholder or low-entropy value."
    if any(ch in value for ch in "\r\n\0"):
        return f"{name} contains an invalid control character."
    return ""


def audit_environment(values: dict[str, str] | None = None, *, require_production: bool = True, check_dependencies: bool = False) -> dict:
    env = dict(os.environ)
    if values:
        env.update({str(k): str(v) for k, v in values.items()})
    errors: list[str] = []
    warnings: list[str] = []
    production = truthy(env.get("EINVITE_PRODUCTION"))
    durable = truthy(env.get("EINVITE_REQUIRE_DURABLE_SERVICES", "1" if production else "0"))
    if require_production and not production:
        errors.append("EINVITE_PRODUCTION must be enabled for a production preflight.")

    public_url = env.get("EINVITE_PUBLIC_BASE_URL", "").strip()
    url_problem = _url_error(public_url, {"https"}, "EINVITE_PUBLIC_BASE_URL", root_only=True)
    if url_problem:
        errors.append(url_problem)
    public_hostname = (urlparse(public_url).hostname or "").lower().rstrip(".") if not url_problem else ""
    allowed_hosts = {item.strip().lower().rstrip(".") for item in env.get("EINVITE_ALLOWED_HOSTS", "").split(",") if item.strip()}
    if any(item in {"*", "0.0.0.0", "::"} or not valid_exact_host(item) for item in allowed_hosts):
        errors.append("EINVITE_ALLOWED_HOSTS must contain only exact DNS hostnames or loopback addresses.")
    if public_hostname and public_hostname not in allowed_hosts:
        errors.append("EINVITE_ALLOWED_HOSTS must include the EINVITE_PUBLIC_BASE_URL hostname.")
    if not truthy(env.get("EINVITE_COOKIE_SECURE")):
        errors.append("EINVITE_COOKIE_SECURE must be enabled in production.")
    if production and not truthy(env.get("EINVITE_REQUIRE_VERIFIED_EMAIL", "1")):
        errors.append("EINVITE_REQUIRE_VERIFIED_EMAIL must be enabled in production.")
    if production and truthy(env.get("EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP")):
        errors.append("EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP must be disabled in production.")
    if production and truthy(env.get("EINVITE_DISCLOSE_HEALTH_DETAILS")):
        warnings.append("Detailed public health responses expose operational metadata; keep EINVITE_DISCLOSE_HEALTH_DETAILS disabled unless the endpoint is access-controlled upstream.")
    if production and not truthy(env.get("EINVITE_REQUIRE_MALWARE_SCAN")):
        errors.append("EINVITE_REQUIRE_MALWARE_SCAN must be enabled in production.")

    secrets = {name: env.get(name, "").strip() for name in SECRET_NAMES}
    for name, value in secrets.items():
        problem = _secret_error(name, value)
        if problem:
            errors.append(problem)
    present_secrets = [value for value in secrets.values() if value]
    if len(present_secrets) != len(set(present_secrets)):
        errors.append("Upload, media, and guest-token signing secrets must be distinct.")

    database_url = env.get("EINVITE_DATABASE_URL", "").strip()
    if database_url:
        problem = _url_error(database_url, {"postgres", "postgresql"}, "EINVITE_DATABASE_URL")
        if problem:
            errors.append(problem)
        else:
            parsed = urlparse(database_url)
            if not parsed.username or not parsed.password or PLACEHOLDER.search(parsed.password):
                errors.append("EINVITE_DATABASE_URL must contain non-placeholder PostgreSQL credentials.")
    elif durable:
        errors.append("EINVITE_DATABASE_URL is required when durable production services are enabled.")
    else:
        warnings.append("SQLite is enabled; use PostgreSQL before running multiple web or worker instances.")

    redis_url = env.get("EINVITE_REDIS_URL", "").strip()
    if redis_url:
        problem = _url_error(redis_url, {"redis", "rediss"}, "EINVITE_REDIS_URL")
        if problem:
            errors.append(problem)
        elif durable and not urlparse(redis_url).password:
            errors.append("EINVITE_REDIS_URL must use authentication in durable production mode.")
    elif durable:
        errors.append("EINVITE_REDIS_URL is required when durable production services are enabled.")
    else:
        warnings.append("Redis is not configured; rate limits remain process-local.")

    provider = env.get("EINVITE_OBJECT_STORAGE_PROVIDER", "local").strip().lower() or "local"
    if provider not in {"local", "s3", "r2", "minio"}:
        errors.append("EINVITE_OBJECT_STORAGE_PROVIDER must be local, s3, r2, or minio.")
    if durable and provider == "local":
        errors.append("Durable production mode requires S3-compatible object storage instead of local media storage.")
    if provider != "local":
        bucket = env.get("EINVITE_OBJECT_STORAGE_BUCKET", "").strip()
        access_key = env.get("EINVITE_OBJECT_STORAGE_ACCESS_KEY", "").strip()
        secret_key = env.get("EINVITE_OBJECT_STORAGE_SECRET_KEY", "").strip()
        endpoint = env.get("EINVITE_OBJECT_STORAGE_ENDPOINT", "").strip()
        if not bucket or PLACEHOLDER.search(bucket):
            errors.append("EINVITE_OBJECT_STORAGE_BUCKET must be configured with a non-placeholder bucket name.")
        if not access_key or not secret_key or PLACEHOLDER.search(access_key) or PLACEHOLDER.search(secret_key):
            errors.append("Object-storage access and secret keys must both be configured with non-placeholder values.")
        if provider in {"r2", "minio"} and not endpoint:
            errors.append("R2 and MinIO require EINVITE_OBJECT_STORAGE_ENDPOINT.")
        if endpoint:
            schemes = {"https"}
            if truthy(env.get("EINVITE_ALLOW_INSECURE_OBJECT_STORAGE")):
                schemes.add("http")
            problem = _url_error(endpoint, schemes, "EINVITE_OBJECT_STORAGE_ENDPOINT")
            if problem:
                errors.append(problem)
        cdn = env.get("EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL", "").strip()
        if cdn:
            problem = _url_error(cdn, {"https"}, "EINVITE_OBJECT_STORAGE_PUBLIC_BASE_URL", root_only=True)
            if problem:
                errors.append(problem)

    backup_provider = env.get("EINVITE_BACKUP_PROVIDER", "local").strip().lower() or "local"
    if durable and backup_provider == "local":
        errors.append("Durable production mode requires non-local backup storage.")

    trusted = [item.strip() for item in env.get("EINVITE_TRUSTED_PROXY_IPS", "").split(",") if item.strip()]
    if any(item in {"*", "0.0.0.0/0", "::/0"} for item in trusted):
        errors.append("EINVITE_TRUSTED_PROXY_IPS must not trust every address.")
    elif any(not _valid_proxy_ip(item) for item in trusted):
        errors.append("EINVITE_TRUSTED_PROXY_IPS must contain exact IP addresses, not hostnames or CIDR ranges.")
    if not trusted:
        warnings.append("No trusted reverse-proxy IPs are configured; forwarded headers will be ignored.")

    dependencies: dict[str, bool] = {}
    if check_dependencies:
        required = {"psycopg": bool(database_url), "redis": bool(redis_url), "boto3": provider != "local"}
        for module, needed in required.items():
            available = importlib.util.find_spec(module) is not None
            dependencies[module] = available
            if needed and not available:
                errors.append(f"Required production dependency is missing: {module}.")

    return {
        "ok": not errors,
        "production": production,
        "durableServices": durable,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "publicOriginConfigured": not bool(url_problem),
            "database": "postgresql" if database_url.startswith(("postgres://", "postgresql://")) else "sqlite",
            "redisConfigured": bool(redis_url),
            "objectStorageProvider": provider,
            "backupProvider": backup_provider,
            "trustedProxyCount": len(trusted),
            "allowedHostCount": len(allowed_hosts),
            "malwareScanRequired": truthy(env.get("EINVITE_REQUIRE_MALWARE_SCAN")),
            "stableSecretsConfigured": all(not _secret_error(name, value) for name, value in secrets.items()),
        },
        "dependencies": dependencies,
    }


def validate_production_environment(values: dict[str, str] | None = None) -> list[str]:
    return list(audit_environment(values, require_production=True)["errors"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate E-invitation production configuration without revealing secrets.")
    parser.add_argument("--env-file", type=Path, help="Optional dotenv file to validate on top of the current environment")
    parser.add_argument("--check-dependencies", action="store_true", help="Also verify optional production Python modules are installed")
    parser.add_argument("--allow-non-production", action="store_true", help="Do not require EINVITE_PRODUCTION=1")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        values = load_env_file(args.env_file) if args.env_file else None
        report = audit_environment(values, require_production=not args.allow_non_production, check_dependencies=args.check_dependencies)
    except Exception as exc:
        report = {"ok": False, "errors": [str(exc)], "warnings": [], "summary": {}, "dependencies": {}}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    else:
        print("PRODUCTION_PREFLIGHT_PASSED" if report["ok"] else "PRODUCTION_PREFLIGHT_FAILED")
        for error in report.get("errors", []):
            print(f"ERROR: {error}")
        for warning in report.get("warnings", []):
            print(f"WARNING: {warning}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
