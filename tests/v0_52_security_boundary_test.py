#!/usr/bin/env python3
"""Live regression coverage for private-file and malware-scan boundaries."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return int(sock.getsockname()[1])


def request(url,method="GET",headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,method=method,headers=headers or {}),timeout=5) as response:
            return response.status,response.headers,response.read()
    except urllib.error.HTTPError as error:
        return error.code,error.headers,error.read()
    except (urllib.error.URLError,ConnectionError,OSError):
        # The server process may not be listening yet (startup race during the
        # readiness poll below); treat as "not ready" instead of crashing the test.
        return 0,None,b""


def verify_private_files_are_not_web_files():
    port=free_port()
    with tempfile.TemporaryDirectory(prefix="einvite-security-boundary-") as data:
        env={
            **os.environ,
            "EINVITE_DATA_DIR":data,
            "EINVITE_DATABASE_URL":"",
            "EINVITE_REDIS_URL":"",
            "EINVITE_OBJECT_STORAGE_PROVIDER":"local",
            "EINVITE_MALWARE_SCANNER_MODE":"",
            "EINVITE_REQUIRE_MALWARE_SCAN":"0",
            "EINVITE_ALLOWED_HOSTS":"127.0.0.1,localhost",
            "PYTHONUTF8":"1",
        }
        process=subprocess.Popen(
            [sys.executable,str(ROOT/"server.py"),"--host","127.0.0.1","--port",str(port)],
            cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        )
        try:
            base=f"http://127.0.0.1:{port}"
            deadline=time.time()+30
            while time.time()<deadline and process.poll() is None:
                status,_,body=request(base+"/api/health")
                if status==200 and json.loads(body)["ok"]:break
                time.sleep(.15)
            else:raise AssertionError("security test server did not become ready")

            for path in (
                "/server.py","/security_v13.py","/.env.example","/.gitignore",
                "/data/invites.db","/data/.guest-token-secret","/data/",
                "/tests/security_regression_test.py","/backup.py",
                "/host-einvite-laptop.ps1","/V0_52_RELEASE_FILE_HASHES.sha256",
                "/BUILD_INFO.json","/route-bundles-v15.json","/page-assets-v15.json",
                "/licenses/%2e%2e/server.py",
            ):
                status,_,body=request(base+path)
                assert status in {403,404},(path,status,body[:120])
            status,_,_=request(base+"/server.py",method="HEAD")
            assert status in {403,404},status
            status,_,body=request(base+"/api/health",headers={"Host":"attacker.invalid"})
            assert status==421 and json.loads(body)["code"]=="host_rejected",(status,body)

            for path in (
                "/bundle-index-v15.css","/service-worker.js",
                "/vendor/momentkh.js",
                "/assets/fonts/noto-sans-latin-400.woff2",
                "/licenses/fonts/Noto-OFL-1.1.txt",
            ):
                status,headers,body=request(base+path)
                assert status==200,(path,status,body[:120])
                assert headers.get("X-Content-Type-Options")=="nosniff"
                assert headers.get("Content-Security-Policy")

            status,_,body=request(base+"/api/health")
            health=json.loads(body)
            dependencies=health["dependencies"]
            assert {"malwareScanner","malwareScanReady","malwareScanRequired"}<=set(dependencies)
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)


def verify_required_scanner_fails_closed():
    with tempfile.TemporaryDirectory(prefix="einvite-required-scanner-") as data:
        env={
            **os.environ,
            "EINVITE_DATA_DIR":data,
            "EINVITE_MALWARE_SCANNER_COMMAND":"",
            "EINVITE_MALWARE_SCANNER_MODE":"none",
            "EINVITE_REQUIRE_MALWARE_SCAN":"1",
            "PYTHONPATH":str(ROOT),
            "PYTHONUTF8":"1",
        }
        code=(
            "import server\n"
            "try: server.scan_material_bytes(b'not-a-real-upload','application/octet-stream','blocked.bin')\n"
            "except ValueError as exc:\n"
            " assert 'required' in str(exc).lower() and 'blocked' in str(exc).lower(); print('BLOCKED')\n"
            "else: raise AssertionError('required scanner accepted an unscanned upload')\n"
        )
        result=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30)
        assert result.returncode==0 and "BLOCKED" in result.stdout,result.stdout+result.stderr


def main():
    verify_private_files_are_not_web_files()
    verify_required_scanner_fails_closed()
    print("V0_52_SECURITY_BOUNDARY_TEST_PASSED")
    return 0


if __name__=="__main__":raise SystemExit(main())
