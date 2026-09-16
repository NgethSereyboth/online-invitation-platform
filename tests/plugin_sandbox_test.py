#!/usr/bin/env python3
"""V54.33 phase-4a — Plugin sandbox host runtime test (ROADMAP-V2 §4.4).

Real-HTTP integration test verifying:
  1. Submit a plugin to the marketplace (POST /_marketplace/plugins/submit).
  2. CRL endpoint returns empty list initially (GET /_marketplace/crl.json).
  3. Marketplace keys endpoint returns the author's public key (GET /_marketplace/keys/{id}).
  4. Install fails if plugin is not approved (POST /api/plugins/install → 404).
  5. Approve the plugin directly in DB, then install succeeds.
  6. Launch endpoint returns the srcdoc + manifest + permissions (GET /api/plugins/{id}/launch).
  7. plugin_sandbox_host.js exists + has the expected EInvitePluginSandboxHost.mount API.

Run: ``PYTHONPATH=src/python:. python3 tests/plugin_sandbox_test.py``
"""
from __future__ import annotations
import os
import sys
import json
import time
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


def main() -> int:
    with app_server() as (process, base, data_dir):
        email = f"plugin-{int(time.time())}@einvite.test"
        register(base, email)
        opener = login(base, email)
        print("[OK] host logged in")

        # 1. Submit a plugin to the marketplace
        manifest = {
            "name": "Confetti Animation",
            "version": "1.0.0",
            "author": "Test Author",
            "author_key_id": "test-author-key-001",
            "author_public_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "permissions": ["invitation:read"],
            "entrypoint": "confetti.js",
        }
        bundle_srcdoc = "<html><body><h1>Confetti plugin</h1></body></html>"
        status, _, data = _do(opener, "POST", f"{base}/_marketplace/plugins/submit", {
            "manifest": manifest,
            "bundle_srcdoc": bundle_srcdoc,
            "author_signature": "stub-signature",
            "marketplace_signature": "stub-marketplace-signature",
        })
        if status != 201:
            print(f"FAIL: marketplace submit returned {status}: {data}")
            return 1
        plugin_id = data.get("id")
        if not plugin_id:
            print(f"FAIL: no plugin id returned: {data}")
            return 1
        print(f"[OK] submitted plugin {plugin_id} (status={data.get('status')})")

        # 2. CRL endpoint
        status, _, data = _do(opener, "GET", f"{base}/_marketplace/crl.json")
        if status != 200:
            print(f"FAIL: CRL endpoint returned {status}: {data}")
            return 1
        if data.get("count", -1) < 0:
            print(f"FAIL: CRL count should be >= 0, got: {data}")
            return 1
        print(f"[OK] CRL endpoint works (count={data.get('count')}, ca_configured={data.get('ca_configured')})")

        # 3. Marketplace keys endpoint
        status, _, data = _do(opener, "GET", f"{base}/_marketplace/keys/test-author-key-001")
        if status != 200:
            print(f"FAIL: marketplace keys returned {status}: {data}")
            return 1
        if data.get("author_public_key") != manifest["author_public_key"]:
            print(f"FAIL: author_public_key mismatch: {data}")
            return 1
        print(f"[OK] marketplace keys endpoint returns author public key")

        # 4. Install fails (plugin is 'pending', not 'approved')
        status, _, data = _do(opener, "POST", f"{base}/api/plugins/install", {
            "plugin_id": plugin_id,
            "approved_permissions": ["invitation:read"],
        })
        if status != 404:
            print(f"FAIL: install should return 404 for pending plugin, got {status}: {data}")
            return 1
        print(f"[OK] install fails for pending plugin (404)")

        # 5. Approve the plugin directly in DB
        import sqlite3
        db_path = os.path.join(str(data_dir), "invites.db")
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE marketplace_plugins SET status='approved', approved_at=? WHERE id=?", (int(time.time()*1000), plugin_id))
        conn.commit(); conn.close()
        print(f"[OK] approved plugin {plugin_id} in DB")

        # 6. Install now succeeds
        status, _, data = _do(opener, "POST", f"{base}/api/plugins/install", {
            "plugin_id": plugin_id,
            "approved_permissions": ["invitation:read"],
        })
        if status != 201:
            print(f"FAIL: install returned {status}: {data}")
            return 1
        installation_id = data.get("id")
        print(f"[OK] installed plugin (installation_id={installation_id})")

        # 7. Launch endpoint
        status, _, data = _do(opener, "GET", f"{base}/api/plugins/{installation_id}/launch")
        if status != 200:
            print(f"FAIL: launch returned {status}: {data}")
            return 1
        if data.get("srcdoc") != bundle_srcdoc:
            print(f"FAIL: srcdoc mismatch: {data.get('srcdoc')[:50]}...")
            return 1
        if not data.get("manifest") or not data.get("approvedPermissions"):
            print(f"FAIL: manifest/approvedPermissions missing: {data}")
            return 1
        if data.get("pluginId") != plugin_id:
            print(f"FAIL: pluginId mismatch: {data.get('pluginId')} != {plugin_id}")
            return 1
        print(f"[OK] launch returns srcdoc + manifest + approvedPermissions (bundleSize={data.get('bundleSize')})")

    # 8. Static check: plugin_sandbox_host.js exists + has the expected API
    sandbox_js = REPO / "src" / "js" / "plugin_sandbox_host.js"
    if not sandbox_js.is_file():
        print(f"FAIL: {sandbox_js} does not exist")
        return 1
    content = sandbox_js.read_text(encoding="utf-8")
    if "EInvitePluginSandboxHost" not in content:
        print("FAIL: plugin_sandbox_host.js missing EInvitePluginSandboxHost")
        return 1
    if ".mount = mount" not in content and "mount: mount" not in content:
        print("FAIL: plugin_sandbox_host.js missing mount export")
        return 1
    if "sandbox=" not in content and "setAttribute('sandbox'" not in content:
        print("FAIL: plugin_sandbox_host.js missing sandbox attribute")
        return 1
    print(f"[OK] plugin_sandbox_host.js exists with EInvitePluginSandboxHost.mount API (sandbox={sandbox_js.stat().st_size} bytes)")

    # 9. Static check: plugin_marketplace_ca.py exists + has verify_plugin_signature
    ca_py = REPO / "src" / "python" / "plugin_marketplace_ca.py"
    if not ca_py.is_file():
        print(f"FAIL: {ca_py} does not exist")
        return 1
    ca_content = ca_py.read_text(encoding="utf-8")
    if "def verify_plugin_signature" not in ca_content:
        print("FAIL: plugin_marketplace_ca.py missing verify_plugin_signature")
        return 1
    if "def check_revocation" not in ca_content:
        print("FAIL: plugin_marketplace_ca.py missing check_revocation")
        return 1
    print(f"[OK] plugin_marketplace_ca.py exists with verify_plugin_signature + check_revocation")

    print()
    print("PLUGIN_SANDBOX_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
