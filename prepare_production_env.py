#!/usr/bin/env python3
"""Create a private production dotenv file with independent random secrets."""
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path
from urllib.parse import quote, urlparse

from production_preflight import audit_environment, load_env_file

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / ".env.production.example"


def validate_origin(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("--public-url must be an HTTPS origin without credentials, path, query, or fragment")
    return value.strip().rstrip("/")


def generate_values() -> dict[str, str]:
    postgres = secrets.token_urlsafe(36)
    redis = secrets.token_urlsafe(36)
    minio_access = secrets.token_hex(12)
    minio_secret = secrets.token_urlsafe(40)
    return {
        "REPLACE_POSTGRES_PASSWORD": postgres,
        "REPLACE_REDIS_PASSWORD": redis,
        "REPLACE_MINIO_ACCESS_KEY": minio_access,
        "REPLACE_MINIO_SECRET_KEY": minio_secret,
        "REPLACE_UPLOAD_SIGNING_SECRET": secrets.token_urlsafe(48),
        "REPLACE_MEDIA_SIGNING_SECRET": secrets.token_urlsafe(48),
        "REPLACE_GUEST_TOKEN_SECRET": secrets.token_urlsafe(48),
        "postgres_url_password": quote(postgres, safe=""),
        "redis_url_password": quote(redis, safe=""),
    }


def create_environment(output: Path, public_url: str, trusted_proxy_ips: str = "") -> Path:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing environment file: {output}")
    text = TEMPLATE.read_text(encoding="utf-8")
    generated = generate_values()
    public_origin = validate_origin(public_url)
    public_hostname = urlparse(public_origin).hostname
    if not public_hostname:
        raise ValueError("--public-url does not contain a hostname")
    text = text.replace("https://invite.example.com", public_origin)
    text = text.replace("EINVITE_ALLOWED_HOSTS=invite.example.com", f"EINVITE_ALLOWED_HOSTS={public_hostname}")
    # URL fields need percent-encoded passwords; replace them before the raw
    # credential placeholders used by Compose and provider SDKs.
    text = text.replace(
        "postgresql://einvite:REPLACE_POSTGRES_PASSWORD@postgres:5432/einvite",
        f"postgresql://einvite:{generated['postgres_url_password']}@postgres:5432/einvite",
    )
    text = text.replace(
        "redis://:REPLACE_REDIS_PASSWORD@redis:6379/0",
        f"redis://:{generated['redis_url_password']}@redis:6379/0",
    )
    for placeholder in (
        "REPLACE_POSTGRES_PASSWORD",
        "REPLACE_REDIS_PASSWORD",
        "REPLACE_MINIO_ACCESS_KEY",
        "REPLACE_MINIO_SECRET_KEY",
        "REPLACE_UPLOAD_SIGNING_SECRET",
        "REPLACE_MEDIA_SIGNING_SECRET",
        "REPLACE_GUEST_TOKEN_SECRET",
    ):
        text = text.replace(placeholder, generated[placeholder])
    text = text.replace("EINVITE_TRUSTED_PROXY_IPS=", f"EINVITE_TRUSTED_PROXY_IPS={trusted_proxy_ips.strip()}", 1)
    # Optional billing integration is intentionally disabled by default in a generated
    # production environment. Operators can populate these values later; leaving
    # template placeholders would make the generated environment fail its own
    # production preflight.
    for key in (
        "EINVITE_BILLING_PROVIDER_NAME",
        "EINVITE_BILLING_CHECKOUT_ENDPOINT",
        "EINVITE_BILLING_API_KEY",
        "EINVITE_BILLING_WEBHOOK_SECRET",
    ):
        lines = text.splitlines()
        text = "\n".join((f"{key}=" if line.startswith(key + "=") else line) for line in lines) + ("\n" if text.endswith("\n") else "")
    if "REPLACE_" in text:
        raise RuntimeError("The production template contains an unhandled placeholder")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    try:
        os.chmod(output, 0o600)
    except OSError:
        pass
    report = audit_environment(load_env_file(output))
    if not report["ok"]:
        output.unlink(missing_ok=True)
        raise RuntimeError("Generated environment did not pass production preflight: " + " ".join(report["errors"]))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate .env.production without printing its secrets")
    parser.add_argument("--public-url", required=True, help="Canonical external HTTPS origin")
    parser.add_argument("--output", type=Path, default=ROOT / ".env.production")
    parser.add_argument("--trusted-proxy-ips", default="", help="Comma-separated exact reverse-proxy source IPs")
    args = parser.parse_args(argv)
    try:
        path = create_environment(args.output, args.public_url, args.trusted_proxy_ips)
    except Exception as exc:
        print(f"PRODUCTION_ENV_NOT_CREATED: {exc}")
        return 1
    print(f"PRODUCTION_ENV_CREATED: {path}")
    print("Secrets were written to the file and were not printed. Store a protected backup before deployment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
