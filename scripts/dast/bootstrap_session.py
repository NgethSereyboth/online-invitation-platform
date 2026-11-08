#!/usr/bin/env python3
"""Create a disposable DAST account and establish a real authenticated session.

The server uses an HttpOnly ``einvite_session`` cookie plus the double-submit
``einvite_csrf`` cookie. ZAP is given both through its request-replacer config;
the values never enter the repository, the uploaded report directory, or stdout.

The flow deliberately registers once, logs out, and logs in again so the
session used by the scan is created by the normal login handler.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path


class BootstrapError(RuntimeError):
    pass


def call(opener, base, path, *, method="GET", body=None, headers=None, expected=None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base + path,
        data=payload,
        method=method,
        headers=request_headers,
    )
    try:
        with opener.open(request, timeout=20) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    if expected is not None and status not in expected:
        raise BootstrapError(f"{method} {path}: expected {expected}, got {status}: {raw[:500]!r}")
    return status, raw


def cookie_map(jar):
    values = {}
    for cookie in jar:
        values[cookie.name] = cookie.value
    return values


def write_private(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_zap_config(path, text):
    # The ZAP container may have a different UID from the Actions runner and
    # must be able to read the replacer config from the read-only mount. The
    # session JSON remains mode 600; only this disposable config is 0644.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o644)


def write_public(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replacer_config(cookie_header, csrf):
    lines = [
        "replacer.full_list(0).description=DAST session cookie",
        "replacer.full_list(0).enabled=true",
        "replacer.full_list(0).matchtype=REQ_HEADER",
        "replacer.full_list(0).matchstr=Cookie",
        "replacer.full_list(0).regex=false",
        f"replacer.full_list(0).replacement={cookie_header}",
        "replacer.full_list(1).description=DAST CSRF token",
        "replacer.full_list(1).enabled=true",
        "replacer.full_list(1).matchtype=REQ_HEADER",
        "replacer.full_list(1).matchstr=X-CSRF-Token",
        "replacer.full_list(1).regex=false",
        f"replacer.full_list(1).replacement={csrf}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--email", default=os.environ.get("DAST_EMAIL", ""))
    parser.add_argument("--password", default=os.environ.get("DAST_PASSWORD", ""))
    parser.add_argument("--session-file", required=True)
    parser.add_argument("--zap-config", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    base = args.base.rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise BootstrapError("DAST fixture base must be a loopback HTTP origin")

    email = args.email.strip().lower()
    password = args.password
    if not email or not password:
        raise BootstrapError("DAST_EMAIL and DAST_PASSWORD must be set")
    if not email.endswith("@example.com"):
        # The workflow generates this shape; a configured secret is allowed,
        # but the local database is still disposable.
        print(f"Using configured synthetic account {email}", flush=True)

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    origin = base

    status, _ = call(
        opener,
        base,
        "/api/auth/register",
        method="POST",
        body={"email": email, "password": password},
        headers={"Origin": origin},
    )
    if status == 201:
        # Prove the fixture is not just using the registration session:
        # log out with the CSRF pair, then perform the real login below.
        cookies = cookie_map(jar)
        csrf = cookies.get("einvite_csrf")
        if not csrf:
            raise BootstrapError("registration did not set einvite_csrf")
        call(
            opener,
            base,
            "/api/auth/logout",
            method="POST",
            body={},
            headers={"Origin": origin, "X-CSRF-Token": csrf},
            expected=(200,),
        )
    elif status != 409:
        raise BootstrapError(f"registration failed with HTTP {status}")

    call(
        opener,
        base,
        "/api/auth/login",
        method="POST",
        body={"email": email, "password": password},
        headers={"Origin": origin},
        expected=(201,),
    )

    status, raw = call(opener, base, "/api/auth/me", expected=(200,))
    payload = json.loads(raw or b"{}")
    user = payload.get("user")
    if not user:
        raise BootstrapError("login did not create an authenticated session")

    cookies = cookie_map(jar)
    session_cookie = cookies.get("einvite_session")
    csrf = cookies.get("einvite_csrf")
    if not session_cookie or not csrf:
        raise BootstrapError("login did not set both session and CSRF cookies")
    if any("\n" in value or "\r" in value for value in (session_cookie, csrf)):
        raise BootstrapError("cookie values contain a line break")

    cookie_header = f"einvite_session={session_cookie}; einvite_csrf={csrf}"
    write_private(
        args.session_file,
        json.dumps(
            {
                "base": base,
                "email": email,
                "session_cookie": session_cookie,
                "csrf_token": csrf,
                "cookie_header": cookie_header,
            },
            indent=2,
        )
        + "\n",
    )
    write_zap_config(args.zap_config, replacer_config(cookie_header, csrf))
    write_public(
        args.summary,
        json.dumps(
            {
                "authenticated": True,
                "email": email,
                "userId": user.get("id"),
                "base": base,
                "cookieNames": ["einvite_session", "einvite_csrf"],
                "csrfPresent": True,
            },
            indent=2,
        )
        + "\n",
    )
    print(f"DAST_AUTHENTICATED {email}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(f"DAST_BOOTSTRAP_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
