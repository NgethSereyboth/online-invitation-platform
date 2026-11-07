#!/usr/bin/env python3
"""Verify that the policy proxy carries the disposable authenticated session.

This runs before ZAP. It proves three things independently of the scanner:
1. the proxy forwards the cookie/CSRF pair to the real app;
2. ``/api/auth/me`` returns the fixture user;
3. a non-destructive policy test cannot mutate the fixture (POST is blocked).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


class VerificationError(RuntimeError):
    pass


def request(base, path, *, method="GET", cookie_header="", csrf="", body=None):
    headers = {
        "Accept": "application/json",
        "Cookie": cookie_header,
        "X-CSRF-Token": csrf,
    }
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--session-file", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    session = json.loads(Path(args.session_file).read_text(encoding="utf-8"))
    base = args.base.rstrip("/")
    cookie_header = session["cookie_header"]
    csrf = session["csrf_token"]
    if not cookie_header or not csrf:
        raise VerificationError("session file is missing cookie/CSRF material")

    status, raw = request(base, "/api/auth/me", cookie_header=cookie_header, csrf=csrf)
    if status != 200:
        raise VerificationError(f"/api/auth/me returned HTTP {status}: {raw[:500]!r}")
    payload = json.loads(raw or b"{}")
    user = payload.get("user")
    if not user:
        raise VerificationError("proxy did not establish an authenticated session")
    if str(user.get("email", "")).lower() != str(session["email"]).lower():
        raise VerificationError("authenticated user does not match the fixture account")

    # This POST must be stopped by the read-only proxy. A 405 proves the active
    # scanner cannot create an invitation through the DAST origin.
    blocked_status, _ = request(
        base,
        "/api/invitations",
        method="POST",
        cookie_header=cookie_header,
        csrf=csrf,
        body={},
    )
    if blocked_status != 405:
        raise VerificationError(
            f"non-destructive policy failed: POST /api/invitations returned {blocked_status}"
        )

    summary = {
        "authenticated": True,
        "email": session["email"],
        "userId": user.get("id"),
        "safePolicyBlockedMutation": True,
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"DAST_PROXY_AUTHENTICATED {session['email']}", flush=True)
    print("DAST_SAFE_POLICY_BLOCKED_MUTATION", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"DAST_VERIFICATION_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
