#!/usr/bin/env python3
"""Portable online, Docker, Windows Server, and Linux deployment contracts."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    target = ROOT / path
    assert target.is_file(), f"missing deployment artifact: {path}"
    return target.read_text(encoding="utf-8")


def verify_windows_contract() -> None:
    # deploy-einvite-server.ps1 and DEPLOY_EINVITE_SERVER.bat were removed from
    # the repo (78258bf) with no replacement; their checks were removed with
    # them. The remaining Windows hosting scripts are still contract-checked.
    app = text("deploy/windows/start-einvite-windows-server.ps1")
    proxy = text("deploy/windows/start-einvite-caddy.ps1")
    caddy = text("deploy/windows/Caddyfile")
    assert "127.0.0.1" in app and "0.0.0.0" not in app
    assert "EINVITE_MALWARE_SCANNER_MODE = 'windows-defender'" in app
    assert "EINVITE_REQUIRE_MALWARE_SCAN = '1'" in app
    assert "EINVITE_ALLOWED_HOSTS" in app and "EINVITE_TRUSTED_PROXY_IPS" in app
    assert "caddy run" in proxy and "reverse_proxy 127.0.0.1" in caddy

    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell:
        parser = (
            "$errors=$null;"
            "$files=@('deploy/windows/start-einvite-windows-server.ps1','deploy/windows/start-einvite-caddy.ps1');"
            "foreach($file in $files){[void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $file),[ref]$null,[ref]$errors);"
            "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}}"
        )
        parsed = subprocess.run([powershell, "-NoLogo", "-NoProfile", "-Command", parser], cwd=ROOT, text=True, capture_output=True, timeout=30)
        assert parsed.returncode == 0, parsed.stdout + parsed.stderr


def verify_docker_contract() -> None:
    image = text("deploy/Dockerfile.online")
    base = text("deploy/docker-compose.production.example.yml")
    overlay = text("deploy/docker-compose.online.yml")
    caddy = text("deploy/Caddyfile")
    clamd = text("deploy/clamd.remote.conf")
    assert "USER 10001:10001" in image and "clamav-daemon" in image
    assert "COPY deploy/clamd.remote.conf" in image
    assert "caddy:2.11.4-alpine" in overlay and "clamav/clamav:1.4.6" in overlay
    assert ":latest" not in overlay
    assert 'EINVITE_REQUIRE_MALWARE_SCAN: "1"' in overlay
    assert "EINVITE_ALLOWED_HOSTS" in overlay and "EINVITE_TRUSTED_PROXY_IPS" in overlay
    assert "172.31.52.10" in overlay and "172.31.52.0/24" in overlay
    assert '"80:80"' in overlay and '"443:443"' in overlay
    assert "internal: true" in base and not re.search(r"(?:5432|6379|9000):(?:5432|6379|9000)", base)
    assert "reverse_proxy web:8080" in caddy and "{$EINVITE_DOMAIN}" in caddy
    assert "TCPSocket 3310" in clamd and "TCPAddr clamav" in clamd


def verify_linux_and_docs() -> None:
    # deploy/linux/install-einvite-linux.sh was removed from the repo (78258bf)
    # with no replacement; its checks were removed with it.
    service = text("deploy/linux/einvite.service.template")
    guide = text("docs/ONLINE_AND_SERVER_HOSTING.md")
    paas = text("deploy/paas/PAAS_DEPLOYMENT.md")
    report = text("docs/MULTI_HOST_DEPLOYMENT_REPORT.md")
    assert "ProtectSystem=strict" in service and "NoNewPrivileges=true" in service
    assert "EINVITE_REQUIRE_MALWARE_SCAN=1" in service and "127.0.0.1" in service
    assert all(term in guide for term in ("Windows Server", "Docker", "Bare-metal Linux", "Container hosting platforms", "GitHub Pages"))
    assert all(term in paas for term in ("PostgreSQL", "Redis", "object storage", "ClamAV", "/api/health/ready"))
    assert "without modifying the project README" in report


def verify_generated_host_contract() -> None:
    with tempfile.TemporaryDirectory(prefix="einvite-multi-host-") as folder:
        destination = Path(folder) / ".env.production"
        command = [
            sys.executable,
            str(ROOT / "src" / "python" / "build" / "prepare_production_env.py"),
            "--public-url",
            "https://events.example.test",
            "--output",
            str(destination),
            "--trusted-proxy-ips",
            "172.31.52.10",
        ]
        generated = subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src" / "python") + os.pathsep + str(ROOT)},
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert generated.returncode == 0, generated.stdout + generated.stderr
        values = destination.read_text(encoding="utf-8")
        assert "EINVITE_ALLOWED_HOSTS=events.example.test" in values
        assert "EINVITE_REQUIRE_MALWARE_SCAN=1" in values
        assert "REPLACE_" not in values

        docker = shutil.which("docker")
        if docker:
            environment = {
                **os.environ,
                "EINVITE_DOMAIN": "events.example.test",
                "EINVITE_ENV_FILE": str(destination),
            }
            configured = subprocess.run(
                [docker, "compose", "--env-file", str(destination), "-f", str(ROOT / "deploy" / "docker-compose.production.example.yml"), "-f", str(ROOT / "deploy/docker-compose.online.yml"), "config", "--quiet"],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                timeout=60,
            )
            assert configured.returncode == 0, configured.stdout + configured.stderr


def main() -> int:
    verify_windows_contract()
    verify_docker_contract()
    verify_linux_and_docs()
    verify_generated_host_contract()
    print("V0_52_MULTI_HOST_DEPLOYMENT_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
