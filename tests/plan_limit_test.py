"""Verify optional Free/Creator/Studio quota enforcement without external dependencies."""
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

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def call(base, path, method="GET", body=None, token=None):
    data=None if body is None else json.dumps(body).encode()
    headers={"Content-Type":"application/json"}
    if token:headers["Authorization"]=f"Bearer {token}"
    req=urllib.request.Request(base+path,data=data,method=method,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=8) as response:return response.status,json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:return exc.code,json.loads(exc.read() or b"{}")


def run():
    p=port();base=f"http://127.0.0.1:{p}"
    document={"eventType":"Wedding","fields":{"names":"Quota test"},"objects":{},"designPages":[],"sectionOrder":[],"settings":{}}
    with tempfile.TemporaryDirectory(prefix="e-invitation-website-plan-") as data_dir:
        env={**os.environ,"EINVITE_DATA_DIR":data_dir,"EINVITE_ENFORCE_PLAN_LIMITS":"1"}
        process=subprocess.Popen([sys.executable,"-u",str(ROOT/"server.py"),"--host","127.0.0.1","--port",str(p)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(80):
                try:
                    if call(base,"/api/health")[0]==200:break
                except Exception:pass
                time.sleep(.1)
            else:raise RuntimeError("Server did not start")
            status,registered=call(base,"/api/auth/register","POST",{"email":"quota@example.com","password":"password123"})
            assert status==201,registered;token=registered["token"]
            for n in range(3):
                status,payload=call(base,"/api/invitations","POST",{"slug":f"quota-{n}","document":document},token)
                assert status==201,payload
            status,payload=call(base,"/api/invitations","POST",{"slug":"quota-4","document":document},token)
            assert status==403 and payload.get("code")=="plan_limit_reached",payload
            status,usage=call(base,"/api/account/usage",token=token)
            assert status==200 and usage["enforced"] is True and usage["usage"]["invitations"]==3
            print("PLAN_LIMIT_TEST_PASSED")
        finally:
            process.terminate()
            try:process.wait(timeout=4)
            except subprocess.TimeoutExpired:process.kill()


if __name__=="__main__":run()
