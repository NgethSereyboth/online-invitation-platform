#!/usr/bin/env python3
"""Non-destructive contracts for first-time installation and hosting entry points.

The first-time entry points this test originally covered (FIRST_TIME_SETUP.cmd,
FIRST_TIME_HOSTING_SETUP.cmd, setup-hosting-once.ps1,
deploy/linux/setup-einvite-linux-once.sh) and deploy-einvite-server.ps1 were
removed from the repo (78258bf) with no replacement, so their checks were
removed with them. What remains here covers the live setup artifacts:
``scripts/setup-einvite-complete.ps1`` and the install guide.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

windows_setup = (ROOT / "scripts" / "setup-einvite-complete.ps1").read_text(encoding="utf-8")
assert "Python 3.10 or newer is required" in windows_setup
assert "winget is unavailable" in windows_setup
assert "Windows Server detected" in windows_setup

guide = (ROOT / "docs" / "FIRST_TIME_INSTALL_AND_HOSTING.md").read_text(encoding="utf-8")
for heading in ("Windows 10/11 local setup", "Permanent Docker host", "Windows Server", "Native Linux server with systemd", "Container hosting services", "Required checks before accepting customers"):
    assert heading in guide, heading
for warning in ("cannot run the complete platform", "Never commit", "restore drill"):
    assert warning in guide, warning

print("V0_52_FIRST_TIME_SETUP_CONTRACT_TEST_PASSED")
