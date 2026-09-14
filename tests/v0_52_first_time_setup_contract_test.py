#!/usr/bin/env python3
"""Non-destructive contracts for first-time installation and hosting entry points."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

required = {
    "FIRST_TIME_SETUP.cmd",
    "FIRST_TIME_HOSTING_SETUP.cmd",
    "setup-hosting-once.ps1",
    "FIRST_TIME_INSTALL_AND_HOSTING.md",
    "deploy/linux/setup-einvite-linux-once.sh",
}
for relative in required:
    assert (ROOT / relative).is_file(), relative

quick = (ROOT / "FIRST_TIME_SETUP.cmd").read_text(encoding="utf-8")
assert "setup-einvite-complete.ps1" in quick
assert "-SkipBrowserTests" in quick and "-NoAutoStart" in quick
assert "server.py" in quick and "RunAs" in quick

hosting_cmd = (ROOT / "FIRST_TIME_HOSTING_SETUP.cmd").read_text(encoding="utf-8")
for mode in ("Validate", "Local", "Network", "Docker", "WindowsServer"):
    assert mode in hosting_cmd
assert "setup-hosting-once.ps1" in hosting_cmd

hosting = (ROOT / "setup-hosting-once.ps1").read_text(encoding="utf-8")
for token in (
    "ValidateSet('Validate', 'Local', 'Network', 'Docker', 'WindowsServer')",
    "prepare_production_env.py", "DockerOnline", "WindowsServer",
    "172.31.52.10", "127.0.0.1,::1",
):
    assert token in hosting, token
assert "StopAfterCreate" in hosting and "real Windows Server providers" in hosting
assert not re.search(r"(?i)(password|secret|api[_-]?key)\s*=\s*['\"]?[A-Za-z0-9_-]{12,}", hosting)

windows_setup = (ROOT / "setup-einvite-complete.ps1").read_text(encoding="utf-8")
assert "Python 3.10 or newer is required" in windows_setup
assert "winget is unavailable" in windows_setup
assert "Windows Server detected" in windows_setup

linux = (ROOT / "deploy/linux/setup-einvite-linux-once.sh").read_text(encoding="utf-8")
for token in ("set -Eeuo pipefail", "umask 027", "--install-system-packages", "docker compose version", "clamdscan", "requirements-production.txt"):
    assert token in linux, token
assert "curl |" not in linux and "wget |" not in linux

guide = (ROOT / "FIRST_TIME_INSTALL_AND_HOSTING.md").read_text(encoding="utf-8")
for heading in ("Windows 10/11 local setup", "Permanent Docker host", "Windows Server", "Native Linux server with systemd", "Container hosting services", "Required checks before accepting customers"):
    assert heading in guide, heading
for warning in ("cannot run the complete platform", "Never commit", "restore drill"):
    assert warning in guide, warning

manager = (ROOT / "deploy-einvite-server.ps1").read_text(encoding="utf-8")
for relative in required:
    normalized = relative.replace("/", "\\")
    assert normalized in manager or relative in manager, relative

print("V0_52_FIRST_TIME_SETUP_CONTRACT_TEST_PASSED")
