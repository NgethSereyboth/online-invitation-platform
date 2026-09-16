#!/usr/bin/env python3
"""V54.34 phase-5 — Canva bridge + onboarding flow test (ROADMAP-V2 §4.5/4.6).

Real-HTTP integration test verifying:
  1. Canva auth-status returns configured + connected state.
  2. Canva import via file upload (with malware scan).
  3. Canva export produces a Canva-compatible JSON document.
  4. Canva export-formats endpoint.
  5. Onboarding status (starts at 'signup').
  6. Onboarding complete-step advances the step.
  7. Onboarding skip marks the flow as skipped + completed.

Run: ``PYTHONPATH=src/python:. python3 tests/p5_canva_onboarding_test.py``
"""
from __future__ import annotations
import os
import sys
import json
import time
import base64
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))
from v14_test_utils import app_server  # type: ignore


def _do(opener, method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}; h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with opener.open(req, timeout=10) as r:
            raw = r.read() or b""
            try:
                return r.status, r.headers, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, r.headers, {"_raw": raw.decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        raw = e.read() or b""
        try:
            return e.code, e.headers, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, e.headers, {"_raw": raw.decode("utf-8", errors="replace")}


def register(base, email):
    body = json.dumps({"email": email, "password": "Test1234!Pass", "name": email.split("@")[0]}).encode()
    req = urllib.request.Request(f"{base}/api/auth/register", data=body, method="POST",
                                  headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except urllib.error.HTTPError:
        pass


def login(base, email):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    body = json.dumps({"email": email, "password": "Test1234!Pass"}).encode()
    req = urllib.request.Request(f"{base}/api/auth/login", data=body, method="POST",
                                  headers={"Content-Type": "application/json"})
    opener.open(req, timeout=10).read()
    return opener


def create_invitation(opener, base):
    status, _, data = _do(opener, "POST", f"{base}/api/invitations", {"title": "P5 Canva test", "eventType": "wedding"})
    return data.get("id") or data.get("invitationId")


def main() -> int:
    with app_server() as (process, base, data_dir):
        email = f"p5-{int(time.time())}@einvite.test"
        register(base, email)
        opener = login(base, email)
        print("[OK] host logged in")

        invite_id = create_invitation(opener, base)
        if not invite_id:
            print("FAIL: could not create invitation")
            return 1
        print(f"[OK] created invitation {invite_id}")

        # 1. Canva auth-status
        status, _, data = _do(opener, "GET", f"{base}/api/canva/auth-status")
        if status != 200:
            print(f"FAIL: canva auth-status returned {status}: {data}")
            return 1
        if "configured" not in data or "connected" not in data:
            print(f"FAIL: canva auth-status missing fields: {data}")
            return 1
        print(f"[OK] canva auth-status (configured={data.get('configured')}, connected={data.get('connected')})")

        # 2. Canva export-formats
        status, _, data = _do(opener, "GET", f"{base}/api/canva/export-formats")
        if status != 200 or not data.get("formats"):
            print(f"FAIL: canva export-formats returned {status}: {data}")
            return 1
        if len(data["formats"]) < 2:
            print(f"FAIL: expected at least 2 export formats, got: {data['formats']}")
            return 1
        print(f"[OK] canva export-formats ({len(data['formats'])} formats)")

        # 3. Canva import via file upload (small PNG bytes)
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # minimal PNG header + padding
        status, _, data = _do(opener, "POST", f"{base}/api/canva/import", {
            "file_bytes": base64.b64encode(png_bytes).decode("ascii"),
            "file_name": "test.png",
        })
        if status != 200:
            print(f"FAIL: canva import returned {status}: {data}")
            return 1
        if not data.get("assetKey"):
            print(f"FAIL: canva import missing assetKey: {data}")
            return 1
        print(f"[OK] canva import via file upload (assetKey={data.get('assetKey')[:50]}..., size={data.get('size')})")

        # 4. Canva import via URL (without OAuth configured → 202 pending)
        status, _, data = _do(opener, "POST", f"{base}/api/canva/import", {
            "canva_url": "https://www.canva.com/design/DAFxxxxx/view",
        })
        if status != 202:
            print(f"FAIL: canva URL import should return 202 (pending OAuth), got {status}: {data}")
            return 1
        print(f"[OK] canva URL import returns 202 pending (OAuth required)")

        # 5. Canva export
        status, _, data = _do(opener, "POST", f"{base}/api/canva/export", {
            "invitation_id": invite_id,
        })
        if status != 200:
            print(f"FAIL: canva export returned {status}: {data}")
            return 1
        canva_doc = data.get("canvaDocument")
        if not canva_doc or canva_doc.get("type") != "DESIGN":
            print(f"FAIL: canva export missing canvaDocument with type=DESIGN: {data}")
            return 1
        if "pages" not in canva_doc:
            print(f"FAIL: canva export missing pages: {canva_doc}")
            return 1
        print(f"[OK] canva export produces Canva-compatible JSON (type={canva_doc.get('type')}, pages={len(canva_doc.get('pages', []))})")

        # 6. Onboarding status (starts at 'signup')
        status, _, data = _do(opener, "GET", f"{base}/api/onboarding/status")
        if status != 200:
            print(f"FAIL: onboarding status returned {status}: {data}")
            return 1
        if data.get("step") != "signup":
            print(f"FAIL: onboarding step should be 'signup' initially, got: {data.get('step')}")
            return 1
        if data.get("completed"):
            print(f"FAIL: onboarding should not be completed initially")
            return 1
        print(f"[OK] onboarding status (step={data.get('step')}, completed={data.get('completed')})")

        # 7. Complete 'signup' step → should advance to 'tier'
        status, _, data = _do(opener, "POST", f"{base}/api/onboarding/complete-step", {"step": "signup"})
        if status != 200:
            print(f"FAIL: complete-step signup returned {status}: {data}")
            return 1
        if data.get("nextStep") != "tier":
            print(f"FAIL: next step should be 'tier', got: {data.get('nextStep')}")
            return 1
        print(f"[OK] onboarding signup → tier (completed={data.get('completed')})")

        # 8. Complete 'tier' step → should advance to 'workspace'
        status, _, data = _do(opener, "POST", f"{base}/api/onboarding/complete-step", {"step": "tier"})
        if status != 200 or data.get("nextStep") != "workspace":
            print(f"FAIL: tier → workspace failed: {data}")
            return 1
        print(f"[OK] onboarding tier → workspace")

        # 9. Invalid step
        status, _, data = _do(opener, "POST", f"{base}/api/onboarding/complete-step", {"step": "invalid_step"})
        if status != 400:
            print(f"FAIL: invalid step should return 400, got {status}: {data}")
            return 1
        print(f"[OK] invalid step returns 400")

        # 10. Skip onboarding
        status, _, data = _do(opener, "POST", f"{base}/api/onboarding/skip")
        if status != 200 or not data.get("skipped"):
            print(f"FAIL: skip returned {status}: {data}")
            return 1
        print(f"[OK] onboarding skipped")

        # 11. Status after skip
        status, _, data = _do(opener, "GET", f"{base}/api/onboarding/status")
        if not data.get("skipped") or not data.get("completed"):
            print(f"FAIL: after skip, status should be skipped+completed, got: {data}")
            return 1
        print(f"[OK] onboarding status after skip (skipped={data.get('skipped')}, completed={data.get('completed')})")

    print()
    print("P5_CANVA_ONBOARDING_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
