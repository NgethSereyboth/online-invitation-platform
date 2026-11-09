#!/usr/bin/env python3
"""Read-only API edge-case fuzzer for the QA deep-dive.

Starts an isolated eInvite server with a temporary data directory, then sends
malformed JSON, wrong types, boundary values, null bytes and long Unicode to
the core endpoints. The harness is deliberately non-destructive: it creates its
own account/invitation and only reads or fuzzes those rows.

Exit 0 only when every case returns a bounded client/server error (not 500,
not an HTML traceback) and the fuzz report is written.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "artifacts" / "qa"
ADMIN_EMAIL = "qa-fuzz-admin@example.com"
ADMIN_PASSWORD = "Qa-Fuzz-Passw0rd-2026!"
FAILURES: list[dict] = []
CASES: list[dict] = []


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen, timeout: float = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited early with {process.returncode}")
        try:
            response = requests.get(base + "/api/health", timeout=1)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.15)
    raise RuntimeError("server did not become ready")


def body_excerpt(response: requests.Response, limit: int = 240) -> str:
    text = response.text or ""
    return text.replace("\n", " ")[:limit]


def record(name: str, response: requests.Response, *, allow: set[int]) -> None:
    status = response.status_code
    content_type = response.headers.get("content-type", "")
    excerpt = body_excerpt(response)
    bad = status >= 500 or "traceback" in excerpt.lower() or "internal server error" in excerpt.lower()
    if bad or status not in allow:
        FAILURES.append(
            {
                "case": name,
                "status": status,
                "content_type": content_type,
                "body": excerpt,
                "allowed": sorted(allow),
            }
        )
    CASES.append(
        {
            "case": name,
            "status": status,
            "content_type": content_type,
            "ok": not bad and status in allow,
            "body": excerpt,
        }
    )


def main() -> int:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    data_dir = Path(tempfile.mkdtemp(prefix="einvite-qa-fuzz-"))
    env = {
        **os.environ,
        "EINVITE_DATA_DIR": str(data_dir),
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "1",
        "EINVITE_ADMIN_EMAIL": ADMIN_EMAIL,
        "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
        "EINVITE_DEV_AUTH_TOKENS": "1",
        "PYTHONPATH": os.pathsep.join([str(ROOT / "src" / "python"), str(ROOT)]),
    }
    out = REPORT_DIR / f"api-fuzz-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log = open(data_dir / "server.log", "w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "src" / "python" / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    session = requests.Session()
    session.headers.update({"Origin": base, "Accept": "application/json"})
    # Login/registration probes must not replace the admin session: a successful
    # registration would rotate the cookie and invalidate the admin CSRF token.
    probe = requests.Session()
    probe.headers.update({"Origin": base, "Accept": "application/json"})
    try:
        wait_health(base, process)
        registered = session.post(
            base + "/api/auth/register",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10,
        )
        record("register/bootstrap", registered, allow={201})
        if registered.status_code != 201:
            raise RuntimeError("bootstrap registration failed; see report")
        csrf = registered.json().get("csrfToken", "")
        session.headers.update({"X-CSRF-Token": csrf})
        token = registered.json().get("token", "")
        auth = {"Authorization": f"Bearer {token}"} if token else {}
        mutation_headers = {**auth, "X-CSRF-Token": csrf}

        document = {
            "eventType": "Wedding",
            "fields": {"names": "QA Fuzz", "date": "2026-12-27", "time": "16:00", "venue": "Test Venue"},
            "objects": {},
            "designPages": [],
            "sectionOrder": ["rsvp"],
            "settings": {"rsvpEnabled": True},
            "rsvpFields": [],
        }
        created = session.post(base + "/api/invitations", json={"slug": "qa-fuzz", "document": document}, headers=mutation_headers, timeout=10)
        record("bootstrap/invitation", created, allow={201})
        invite_id = created.json().get("id", "") if created.status_code == 201 else ""

        # Login: malformed and type-confused inputs must not reach the DB layer with a crash.
        raw_headers = {"Content-Type": "application/json"}
        for name, body in [
            ("login/malformed-json", b"{"),
            ("login/empty", {}),
            ("login/email-number", {"email": 123, "password": ADMIN_PASSWORD}),
            ("login/password-list", {"email": ADMIN_EMAIL, "password": []}),
            ("login/password-null-byte", {"email": ADMIN_EMAIL, "password": "x\x00y"}),
            ("login/email-null-byte", {"email": "a\x00b@example.com", "password": "x"}),
        ]:
            if isinstance(body, bytes):
                response = probe.post(base + "/api/auth/login", data=body, headers=raw_headers, timeout=10)
            else:
                response = probe.post(base + "/api/auth/login", json=body, timeout=10)
            record(name, response, allow={400, 401, 422})

        # Registration: malformed, wrong types, length boundary.
        for name, body in [
            ("register/malformed-json", b"{"),
            ("register/missing", {}),
            ("register/email-number", {"email": 123, "password": "StrongPassw0rd!"}),
            ("register/password-number", {"email": "qa-type@example.com", "password": 123}),
            ("register/password-too-long", {"email": "qa-long@example.com", "password": "x" * 201}),
            ("register/email-too-long", {"email": "a" * 250 + "@example.com", "password": "StrongPassw0rd!"}),
            ("register/null-byte-email", {"email": "qa\x00@example.com", "password": "StrongPassw0rd!"}),
            ("register/unicode-email", {"email": "qa.é@example.com", "password": "StrongPassw0rd!"}),
        ]:
            if isinstance(body, bytes):
                response = probe.post(base + "/api/auth/register", data=body, headers=raw_headers, timeout=10)
            else:
                response = probe.post(base + "/api/auth/register", json=body, timeout=10)
            record(name, response, allow={201, 400, 409, 422})

        # Invitation creation: document and slug type boundaries.
        create_cases = [
            ("invite/malformed-json", b"{"),
            ("invite/empty", {}),
            ("invite/document-string", {"slug": "qa-doc-string", "document": "not-a-document"}),
            ("invite/document-list", {"slug": "qa-doc-list", "document": []}),
            ("invite/document-null", {"slug": "qa-doc-null", "document": None}),
            ("invite/names-number", {"slug": "qa-names-number", "document": {**document, "fields": {**document["fields"], "names": 123}}}),
            ("invite/names-null", {"slug": "qa-names-null", "document": {**document, "fields": {**document["fields"], "names": None}}}),
            ("invite/names-null-byte", {"slug": "qa-names-null-byte", "document": {**document, "fields": {**document["fields"], "names": "A\x00B"}}}),
            ("invite/names-unicode", {"slug": "qa-names-unicode", "document": {**document, "fields": {**document["fields"], "names": "👩‍👩‍👧‍👦 مرحبا Ω"}}}),
            ("invite/names-long", {"slug": "qa-names-long", "document": {**document, "fields": {**document["fields"], "names": "A" * 10_000}}}),
            ("invite/slug-number", {"slug": 12345, "document": document}),
        ]
        for name, body in create_cases:
            if isinstance(body, bytes):
                response = session.post(base + "/api/invitations", data=body, headers={**raw_headers, **mutation_headers}, timeout=10)
            else:
                response = session.post(base + "/api/invitations", json=body, headers=mutation_headers, timeout=10)
            record(name, response, allow={201, 400, 409, 422})

        # Pagination/query bounds. All should be a bounded 200/400, never 500.
        query_cases = {
            "pagination/limit-abc": "limit=abc",
            "pagination/limit-float": "limit=1.5",
            "pagination/limit-negative": "limit=-1",
            "pagination/limit-zero": "limit=0",
            "pagination/limit-101": "limit=101",
            "pagination/limit-huge": "limit=999999999999999999999999",
            "pagination/offset-negative": "offset=-5",
            "pagination/offset-abc": "offset=abc",
            "pagination/status-bad": "status=not-a-status",
            "pagination/q-null-byte": "q=%00",
            "pagination/q-long": "q=" + "A" * 10_000,
            "pagination/limit-null-byte": "limit=%00",
        }
        for name, query in query_cases.items():
            response = session.get(base + "/api/invitations?" + query, headers=auth, timeout=10)
            record(name, response, allow={200, 400, 422})

        # Check-in mutation: auth is required; malformed bodies must not crash it.
        if invite_id:
            for name, body in [
                ("checkin/malformed-json", b"{"),
                ("checkin/empty", {}),
                ("checkin/guest-id-number", {"guestId": 123}),
                ("checkin/token-list", {"guestId": "x", "token": []}),
                ("checkin/null-byte", {"guestId": "\x00", "token": "\x00"}),
            ]:
                if isinstance(body, bytes):
                    response = session.post(base + f"/api/invitations/{invite_id}/checkin", data=body, headers={**raw_headers, **mutation_headers}, timeout=10)
                else:
                    response = session.post(base + f"/api/invitations/{invite_id}/checkin", json=body, headers=mutation_headers, timeout=10)
                record(name, response, allow={400, 401, 403, 404, 422})

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "base": base,
            "total": len(CASES),
            "failures": FAILURES,
            "cases": CASES,
        }
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"API_FUZZ_CASES={len(CASES)} FAILURES={len(FAILURES)} REPORT={out}")
        for failure in FAILURES:
            print(f"FAIL {failure['case']} status={failure['status']} body={failure['body']!r}")
        return 1 if FAILURES else 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
        if FAILURES:
            try:
                print("SERVER_LOG_TAIL:")
                print("\n".join((data_dir / "server.log").read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
