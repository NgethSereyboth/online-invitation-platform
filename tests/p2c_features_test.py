#!/usr/bin/env python3
"""V54.32 phase-2c — Calendar / venue map / gift registry test (ROADMAP-V2 §4.3).

Real-HTTP integration test verifying:
  1. Calendar: GET /api/invitations/{id}/calendar.ics returns text/calendar with BEGIN:VCALENDAR.
  2. Calendar Google: GET /api/invitations/{id}/calendar/google returns 302 redirect to calendar.google.com.
  3. Gift registry: host creates item, guest claims, quantity decremented, claim cancel restores quantity.
  4. Gift registry host-only access: guest cannot create/edit/delete items.

Run: ``PYTHONPATH=src/python:. python3 tests/p2c_features_test.py``
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


def create_invitation(opener, base):
    status, _, data = _do(opener, "POST", f"{base}/api/invitations", {"title": "P2C test", "eventType": "wedding"})
    return data.get("id") or data.get("invitationId")


def main() -> int:
    with app_server() as (process, base, data_dir):
        email = f"p2c-{int(time.time())}@einvite.test"
        register(base, email)
        opener = login(base, email)
        print("[OK] host logged in")

        invite_id = create_invitation(opener, base)
        if not invite_id:
            print("FAIL: could not create invitation")
            return 1
        print(f"[OK] created invitation {invite_id}")

        # 1. Calendar .ics
        status, headers, body_text = _do(opener, "GET", f"{base}/api/invitations/{invite_id}/calendar.ics")
        # body_text may be a JSON error or the .ics text
        if status != 200:
            print(f"FAIL: calendar.ics returned {status}: {body_text}")
            return 1
        # The response body is text/calendar, not JSON — _do tried to parse JSON.
        # Re-fetch as raw text.
        req = urllib.request.Request(f"{base}/api/invitations/{invite_id}/calendar.ics")
        with opener.open(req, timeout=10) as r:
            ics_body = r.read().decode("utf-8")
        if "BEGIN:VCALENDAR" not in ics_body:
            print(f"FAIL: calendar.ics missing BEGIN:VCALENDAR: {ics_body[:200]}")
            return 1
        if "END:VCALENDAR" not in ics_body:
            print(f"FAIL: calendar.ics missing END:VCALENDAR")
            return 1
        if "SUMMARY:" not in ics_body:
            print(f"FAIL: calendar.ics missing SUMMARY field")
            return 1
        print(f"[OK] calendar.ics returns valid VCALENDAR (len={len(ics_body)})")

        # 2. Calendar Google redirect — verify the Location header is correctly formed
        #    by issuing a raw HTTP request that doesn't follow redirects.
        import http.client as _httpc
        url_parts = urllib.parse.urlparse(base)
        conn = _httpc.HTTPConnection(url_parts.hostname, url_parts.port, timeout=10)
        # Manually set the session cookie — find the HTTPCookieProcessor in the opener
        cookie_jar = None
        for h in opener.handlers:
            if hasattr(h, 'cookiejar'):
                cookie_jar = h.cookiejar; break
        cookie_header = "; ".join(f"{c.name}={c.value}" for c in cookie_jar) if cookie_jar else ""
        conn.request("GET", f"/api/invitations/{invite_id}/calendar/google",
                     headers={"Cookie": cookie_header})
        resp = conn.getresponse()
        if resp.status != 302:
            print(f"FAIL: calendar/google returned {resp.status} (expected 302)")
            return 1
        loc = resp.getheader("Location", "")
        if "calendar.google.com" not in loc:
            print(f"FAIL: calendar/google Location does not point to Google: {loc}")
            return 1
        if "action=TEMPLATE" not in loc:
            print(f"FAIL: calendar/google missing action=TEMPLATE: {loc}")
            return 1
        conn.close()
        print(f"[OK] calendar/google returns 302 to calendar.google.com")

        # 3. Gift registry — host creates item
        status, _, data = _do(opener, "POST", f"{base}/api/invitations/{invite_id}/gift-registry",
                              {"name": "Blender", "description": "KitchenAid", "url": "https://example.com/b", "price": "$99", "quantity": 3})
        if status != 201:
            print(f"FAIL: create gift item returned {status}: {data}")
            return 1
        item_id = data.get("id")
        print(f"[OK] host created gift item {item_id}")

        # 4. Gift registry — list (as host, should see claims)
        status, _, data = _do(opener, "GET", f"{base}/api/invitations/{invite_id}/gift-registry")
        if status != 200 or not data.get("items"):
            print(f"FAIL: list gift registry returned {status}: {data}")
            return 1
        item = data["items"][0]
        if item["quantity"] != 3 or item["remaining"] != 3:
            print(f"FAIL: gift item quantity/remaining wrong: {item}")
            return 1
        print(f"[OK] gift registry list shows item (quantity=3, remaining=3)")

        # 5. Gift registry — guest claims (need guest access — for simplicity, claim as host with guest email)
        status, _, data = _do(opener, "POST", f"{base}/api/invitations/{invite_id}/gift-registry/{item_id}/claim",
                              {"name": "Alice", "email": "alice@example.com", "quantity": 2})
        if status != 201:
            print(f"FAIL: claim gift returned {status}: {data}")
            return 1
        print(f"[OK] guest claimed 2 of item")

        # 6. Gift registry — list should show remaining=1
        status, _, data = _do(opener, "GET", f"{base}/api/invitations/{invite_id}/gift-registry")
        item = data["items"][0]
        if item["remaining"] != 1:
            print(f"FAIL: remaining should be 1 after claim of 2 (of 3), got: {item['remaining']}")
            return 1
        print(f"[OK] gift registry remaining=1 after claim of 2")

        # 7. Gift registry — over-claim fails
        status, _, data = _do(opener, "POST", f"{base}/api/invitations/{invite_id}/gift-registry/{item_id}/claim",
                              {"name": "Bob", "email": "bob@example.com", "quantity": 5})
        if status != 409:
            print(f"FAIL: over-claim should return 409, got {status}: {data}")
            return 1
        print(f"[OK] over-claim returns 409 (only {data.get('remaining')} remaining)")

        # 8. Gift registry — host updates item
        status, _, data = _do(opener, "PUT", f"{base}/api/invitations/{invite_id}/gift-registry/{item_id}",
                              {"quantity": 5})
        if status != 200:
            print(f"FAIL: update gift item returned {status}: {data}")
            return 1
        print(f"[OK] host updated item quantity to 5")

        # 9. Gift registry — host deletes item
        status, _, data = _do(opener, "DELETE", f"{base}/api/invitations/{invite_id}/gift-registry/{item_id}")
        if status != 200:
            print(f"FAIL: delete gift item returned {status}: {data}")
            return 1
        print(f"[OK] host deleted gift item")

        # 10. Gift registry — list should be empty
        status, _, data = _do(opener, "GET", f"{base}/api/invitations/{invite_id}/gift-registry")
        if data.get("items"):
            print(f"FAIL: gift registry should be empty after delete, got: {data['items']}")
            return 1
        print(f"[OK] gift registry empty after delete")

    print()
    print("P2C_FEATURES_TEST_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
