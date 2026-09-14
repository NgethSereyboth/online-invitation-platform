#!/usr/bin/env python3
"""Production configuration, container, readiness, and secret-safety contract."""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_preflight():
    spec = importlib.util.spec_from_file_location("production_preflight", ROOT / "production_preflight.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_environment() -> dict[str, str]:
    return {
        "EINVITE_PRODUCTION": "1",
        "EINVITE_REQUIRE_DURABLE_SERVICES": "1",
        "EINVITE_PUBLIC_BASE_URL": "https://invite.example.test",
        "EINVITE_ALLOWED_HOSTS": "invite.example.test",
        "EINVITE_COOKIE_SECURE": "1",
        "EINVITE_REQUIRE_MALWARE_SCAN": "1",
        "EINVITE_UPLOAD_SIGNING_SECRET": "Up9!kL2@rT7#vX4$mN8%qW3&yH6*zC1+",
        "EINVITE_MEDIA_SIGNING_SECRET": "Me8!jK3@pS6#uV2$nB9%rQ5&xG7*wD4+",
        "EINVITE_GUEST_TOKEN_SECRET": "Gu7!hJ4@nR5#tU3$mC8%pP6&zF9*vE2+",
        "EINVITE_DATABASE_URL": "postgresql://einvite:Db9!kL2@postgres:5432/einvite",
        "EINVITE_REDIS_URL": "redis://:Rd8!mN3@redis:6379/0",
        "EINVITE_OBJECT_STORAGE_PROVIDER": "minio",
        "EINVITE_OBJECT_STORAGE_BUCKET": "einvite-private",
        "EINVITE_OBJECT_STORAGE_ENDPOINT": "http://minio:9000",
        "EINVITE_OBJECT_STORAGE_REGION": "us-east-1",
        "EINVITE_OBJECT_STORAGE_ACCESS_KEY": "minio-access-9K2m",
        "EINVITE_OBJECT_STORAGE_SECRET_KEY": "minio-secret-7R4p-2L8x",
        "EINVITE_ALLOW_INSECURE_OBJECT_STORAGE": "1",
        "EINVITE_BACKUP_PROVIDER": "object",
        "EINVITE_TRUSTED_PROXY_IPS": "172.20.0.10",
    }


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def verify_live_readiness() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="einvite-production-ready-") as data:
        env = {
            **os.environ,
            "EINVITE_DATA_DIR": data,
            "EINVITE_PRODUCTION": "0",
            "EINVITE_DATABASE_URL": "",
            "EINVITE_REDIS_URL": "",
            "EINVITE_OBJECT_STORAGE_PROVIDER": "local",
            "PYTHONUTF8": "1",
        }
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.time() + 30
            ready = None
            while time.time() < deadline and process.poll() is None:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health/ready", timeout=2) as response:
                        ready = json.loads(response.read().decode("utf-8"))
                    break
                except Exception:
                    time.sleep(0.15)
            assert process.poll() is None and ready and ready["ok"], (process.poll(), ready)
            assert ready["checks"] == {"configuration": True, "database": True, "storage": True, "redis": True}, ready
            assert ready["storage"]["ready"] is True
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health/live", timeout=2) as response:
                live = json.loads(response.read().decode("utf-8"))
            assert live["ok"] and live["status"] == "live"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def verify_invalid_production_fails_closed() -> None:
    secrets = valid_environment()
    with tempfile.TemporaryDirectory(prefix="einvite-production-invalid-") as data:
        env = {
            **os.environ,
            "EINVITE_DATA_DIR": data,
            "EINVITE_PRODUCTION": "1",
            "EINVITE_REQUIRE_DURABLE_SERVICES": "0",
            "EINVITE_PUBLIC_BASE_URL": "http://unsafe.example.test",
            "EINVITE_COOKIE_SECURE": "0",
            "EINVITE_UPLOAD_SIGNING_SECRET": secrets["EINVITE_UPLOAD_SIGNING_SECRET"],
            "EINVITE_MEDIA_SIGNING_SECRET": secrets["EINVITE_MEDIA_SIGNING_SECRET"],
            "EINVITE_GUEST_TOKEN_SECRET": secrets["EINVITE_GUEST_TOKEN_SECRET"],
        }
        result = subprocess.run(
            [sys.executable, str(ROOT / "server.py"), "--host", "127.0.0.1", "--port", "0"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        output = result.stdout + result.stderr
        assert result.returncode != 0 and "Production configuration is invalid" in output, output[-2000:]
        assert "EINVITE_PUBLIC_BASE_URL" in output and "EINVITE_COOKIE_SECURE" in output
        assert all(value not in output for value in (secrets["EINVITE_UPLOAD_SIGNING_SECRET"], secrets["EINVITE_MEDIA_SIGNING_SECRET"], secrets["EINVITE_GUEST_TOKEN_SECRET"]))


def main() -> int:
    preflight = load_preflight()
    good = valid_environment()
    report = preflight.audit_environment(good)
    assert report["ok"], report
    assert report["summary"]["database"] == "postgresql"
    assert report["summary"]["objectStorageProvider"] == "minio"
    serialized = json.dumps(report)
    assert all(value not in serialized for name, value in good.items() if "SECRET" in name or "PASSWORD" in name)

    bad = dict(good)
    bad.update({
        "EINVITE_PUBLIC_BASE_URL": "http://example.test/path?debug=1",
        "EINVITE_COOKIE_SECURE": "0",
        "EINVITE_UPLOAD_SIGNING_SECRET": "replace-me",
        "EINVITE_MEDIA_SIGNING_SECRET": "replace-me",
        "EINVITE_GUEST_TOKEN_SECRET": "replace-me",
        "EINVITE_DATABASE_URL": "sqlite:///data.db",
        "EINVITE_REDIS_URL": "redis://redis:6379/0",
        "EINVITE_OBJECT_STORAGE_PROVIDER": "local",
        "EINVITE_BACKUP_PROVIDER": "local",
        "EINVITE_TRUSTED_PROXY_IPS": "0.0.0.0/0",
    })
    rejected = preflight.audit_environment(bad)
    assert not rejected["ok"] and len(rejected["errors"]) >= 8, rejected
    rejected_json = json.dumps(rejected)
    assert "replace-me" not in rejected_json

    example = ROOT / ".env.production.example"
    values = preflight.load_env_file(example)
    assert values["EINVITE_PRODUCTION"] == "1" and values["EINVITE_REQUIRE_DURABLE_SERVICES"] == "1"
    assert not preflight.audit_environment(values)["ok"], "The committed example must retain rejected placeholders"

    with tempfile.TemporaryDirectory(prefix="einvite-env-generator-") as folder:
        generated_path = Path(folder) / ".env.production"
        command = [sys.executable, str(ROOT / "prepare_production_env.py"), "--public-url", "https://events.example.test", "--output", str(generated_path), "--trusted-proxy-ips", "172.20.0.10"]
        generated = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        assert generated.returncode == 0 and generated_path.is_file(), generated.stdout + generated.stderr
        generated_values = preflight.load_env_file(generated_path)
        assert preflight.audit_environment(generated_values)["ok"]
        assert "REPLACE_" not in generated_path.read_text(encoding="utf-8")
        protected_values = [generated_values[name] for name in preflight.SECRET_NAMES]
        assert len(set(protected_values)) == 3 and all(value not in generated.stdout for value in protected_values)
        refused = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        assert refused.returncode != 0 and "Refusing to overwrite" in refused.stdout

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert all(marker in dockerignore for marker in (".env.*", "!.env.production.example", "*.sqlite3", "*.log"))
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(marker in gitignore for marker in (".env.*", "!.env.production.example", "*.pem", "*.key"))
    checklist = (ROOT / "PRODUCTION_LAUNCH_CHECKLIST.md").read_text(encoding="utf-8")
    assert all(marker in checklist for marker in ("restore drill", "/api/health/ready", "rollback", "private bucket"))
    test_requirements = (ROOT / "requirements-test.txt").read_text(encoding="utf-8")
    assert "playwright==1.61.0" in test_requirements, "Browser release evidence must use the audited toolchain"
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER 10001:10001" in dockerfile and "/api/health/ready" in dockerfile
    assert "PYTHONDONTWRITEBYTECODE=1" in dockerfile and "COPY --chown=einvite:einvite" in dockerfile

    compose = (ROOT / "docker-compose.production.example.yml").read_text(encoding="utf-8")
    assert "EINVITE_ENV_FILE:-.env.production" in compose
    assert "replace-in-secret-manager" not in compose and ":latest" not in compose
    assert "EINVITE_DATABASE_URL:" in compose and "EINVITE_REDIS_URL:" in compose
    assert "condition: service_healthy" in compose and "condition: service_completed_successfully" in compose
    assert "minio-init:" in compose and "no-new-privileges:true" in compose
    assert "127.0.0.1" in compose and "/api/health/ready" in compose

    server = (ROOT / "server.py").read_text(encoding="utf-8")
    preflight_position = server.index("validate_production_environment")
    database_position = server.index("with connect() as _db:_db.execute")
    assert preflight_position < database_position
    assert 'checks["database"]' in server and 'checks["storage"]' in server and 'checks["redis"]' in server
    storage = (ROOT / "platform_v32" / "storage.py").read_text(encoding="utf-8")
    assert "def readiness(self):" in storage and "head_bucket" in storage and ".ready-" in storage

    verify_live_readiness()
    verify_invalid_production_fails_closed()

    print("V0_52_PRODUCTION_DEPLOYMENT_HARDENING_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
