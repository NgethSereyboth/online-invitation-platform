#!/usr/bin/env python3
"""Contract and read-only launcher check for one-command laptop hosting."""
from __future__ import annotations
import subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
batch=(ROOT/'HOST_EINVITE_ON_LAPTOP.bat').read_text(encoding='utf-8')
script=(ROOT/'host-einvite-laptop.ps1').read_text(encoding='utf-8')
guide=(ROOT/'LAPTOP_HOSTING.md').read_text(encoding='utf-8')
assert 'host-einvite-laptop.ps1' in batch and '%*' in batch
for token in ('Install-PythonIfMissing','Python.Python.3.13','--scope user','EINVITE_DATA_DIR','EINVITE_DEV_AUTH_TOKENS = \'0\'','EINVITE_OBJECT_STORAGE_PROVIDER = \'local\'','EINVITE_DATABASE_URL = \'\'','EINVITE_REDIS_URL = \'\'','EINVITE_ALLOWED_HOSTS','EINVITE_MALWARE_SCANNER_MODE','EINVITE_REQUIRE_MALWARE_SCAN','Test-WindowsDefenderScanner','/api/health','qrReady','malwareScanReady','PrivateFirewallRule','Test-PortAvailable','LAPTOP_HOST_CHECK_PASSED','Wait-Process'):
 assert token in script,token
for token in ('private-network HTTP hosting','Do not configure router port forwarding','BACKUP_EINVITE_DATA.bat','-LocalOnly'):
 assert token in guide,token
result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'host-einvite-laptop.ps1'),'-CheckOnly','-SkipFirewall','-NoBrowser','-AllowUploadsWithoutMalwareScan','-Port','18080'],cwd=ROOT,text=True,capture_output=True,encoding='utf-8',errors='replace',timeout=30)
assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
assert 'LAPTOP_HOST_CHECK_PASSED' in result.stdout and 'http://127.0.0.1:18080' in result.stdout,result.stdout
print('V0_52_LAPTOP_HOST_CONTRACT_TEST_PASSED')
