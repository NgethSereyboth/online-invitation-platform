#!/usr/bin/env python3
"""V54.28 (sec-8, ROADMAP-V2 §2.8) — CSP report-only monitoring integration test.

Real-HTTP integration test that exercises the new Content-Security-Policy
report-only pipeline end-to-end:

1. **Header wiring.** Every response now carries THREE CSP-related headers:
   ``Content-Security-Policy`` (the unchanged enforcement header),
   ``Content-Security-Policy-Report-Only`` (a mirror + ``report-uri``), and
   ``Report-To`` (Reporting API group config). The enforcing header MUST be
   byte-identical to its pre-V54.28 value so no production breakage sneaks
   in.

2. **Legacy report shape.** POST a ``csp-report`` body (the legacy
   ``report-uri`` shape) → ``204 No Content`` + a structured ``[csp_report]``
   log line on stdout + (when authenticated) an ``audit_events`` row tagged
   ``csp.violation``.

3. **Unauthenticated case.** POST without a session token → ``204`` + log
   line but NO audit row (guest-page noise must not pollute the audit
   trail).

4. **Authenticated case.** POST with a bearer token → ``204`` + log line +
   audit row whose ``metadata_json`` round-trips the report fields.

5. **Reporting-API shape.** POST the modern ``[{type:csp-violation, body:{...}}]``
   array body → ``204`` + same downstream effects.

6. **Rate limit.** 60 requests within 60 seconds succeed; the 61st returns
   ``429 Too Many Requests``.

7. **Never fail the request.** A malformed body still returns ``204`` (the
   browser must not retry CSP reports on a 5xx).

Acceptance: prints ``SECURITY_CSP_REPORT_TEST_PASSED`` on success.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

from v14_test_utils import app_server, temporary_data

ROOT = Path(__file__).resolve().parents[1]
DB_FILENAME = "invites.db"

# The V54 enforcement CSP — the EXACT string that was on the
# Content-Security-Policy header before V54.28. The report-only header
# must NOT change this; it adds a parallel report-only header instead.
PRE_V54_28_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; media-src 'self' blob:; font-src 'self' data:; "
    "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://w.soundcloud.com; "
    "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'"
)

EMAIL = "sec8-csp@example.com"
PASSWORD = "StrongPassw0rd!-csp-8"


def http_request(base, path, method="POST", body=None, content_type=None,
                 token=None, expected=None, headers=None):
    """Issue a raw HTTP request and return (status, body_bytes, response_headers_dict).

    Unlike the JSON-only ``http_json`` helper in other sec tests, this one
    preserves the raw response body and headers because CSP reports return
    ``204 No Content`` (empty body) and we need to inspect response headers
    like ``Content-Security-Policy``.
    """
    data = None if body is None else (
        body.encode("utf-8") if isinstance(body, str) else body)
    req_headers = dict(headers or {})
    if data is not None and content_type:
        req_headers["Content-Type"] = content_type
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def http_json_request(base, path, method="POST", body=None, token=None,
                      expected=None):
    """JSON-in / JSON-out helper. Returns (status, payload_dict)."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    payload = json.loads(raw or b"{}")
    if expected is not None and status != expected:
        raise AssertionError(
            f"{method} {path}: expected {expected}, got {status}: {payload}")
    return status, payload


def open_db(data_dir: Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(data_dir / DB_FILENAME))
    db.row_factory = sqlite3.Row
    return db


def count_csp_audit_events(db):
    row = db.execute(
        "SELECT COUNT(*) c FROM audit_events WHERE action='csp.violation'"
    ).fetchone()
    return int(row["c"]) if row else 0


def fetch_csp_audit_events(db):
    return db.execute(
        "SELECT id, user_id, action, target_type, metadata_json, ip_address, "
        "created_at FROM audit_events WHERE action='csp.violation' "
        "ORDER BY created_at ASC"
    ).fetchall()


SAMPLE_LEGACY_REPORT = {
    "csp-report": {
        "document-uri": "https://example.com/i/test",
        "referrer": "",
        "violated-directive": "script-src",
        "effective-directive": "script-src",
        "original-policy": "default-src 'self'; script-src 'self'",
        "blocked-uri": "https://evil.com/script.js",
        "line-number": 42,
        "column-number": 1,
        "source-file": "https://example.com/i/test",
    }
}

SAMPLE_REPORTING_API_BODY = [
    {
        "type": "csp-violation",
        "url": "https://example.com/i/test",
        "user_agent": "Mozilla/5.0 (test)",
        "body": {
            "documentURL": "https://example.com/i/test",
            "referrer": "",
            "blockedURL": "https://evil.com/script.js",
            "effectiveDirective": "script-src",
            "originalPolicy": "default-src 'self'; script-src 'self'",
            "lineNumber": 42,
            "columnNumber": 1,
            "sourceFile": "https://example.com/i/test",
        },
    }
]


def assert_eq(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_truthy(value, label):
    if not value:
        raise AssertionError(f"{label}: expected truthy, got {value!r}")


def run_header_check(base):
    """Phase 1: the three CSP-related headers are all present and the
    enforcement header is byte-identical to its pre-V54.28 value."""
    # Any GET will do — the headers are set in end_headers() for every
    # response, including 404s.
    status, _body, headers = http_request(
        base, "/api/health/live", method="GET", expected=None)
    assert_eq(status, 200, "header-check GET /api/health/live status")

    enforcing = headers.get("Content-Security-Policy")
    report_only = headers.get("Content-Security-Policy-Report-Only")
    report_to = headers.get("Report-To")

    assert_eq(enforcing, PRE_V54_28_CSP,
              "enforcing Content-Security-Policy header unchanged")
    # The report-only header must mirror the enforcing policy + report-uri.
    assert_truthy(report_only, "Content-Security-Policy-Report-Only header present")
    assert_truthy(report_only.startswith(PRE_V54_28_CSP),
                  "report-only header mirrors the enforcing policy prefix")
    assert_truthy("report-uri /api/csp-report" in report_only,
                  "report-only header carries report-uri /api/csp-report")
    assert_truthy("report-to csp" in report_only,
                  "report-only header carries report-to csp directive")
    assert_truthy(report_to, "Report-To header present")
    assert_truthy("/api/csp-report" in report_to,
                  "Report-To header points at /api/csp-report")
    assert_truthy('"group":"csp"' in report_to.replace(" ", ""),
                  'Report-To header declares the "csp" group')


def run_unauthenticated_legacy(base, data, log_dir):
    """Phase 2: unauthenticated legacy report → 204 + log line + NO audit row.

    ``data`` is the DB directory (outer tempdir). ``log_dir`` is the
    server's working directory (the inner tempdir created by
    ``app_server``) where ``server-test.log`` lives.
    """
    with open_db(data) as db:
        before = count_csp_audit_events(db)
    status, body, _headers = http_request(
        base, "/api/csp-report",
        body=json.dumps(SAMPLE_LEGACY_REPORT),
        content_type="application/csp-report")
    assert_eq(status, 204, "unauthenticated legacy POST /api/csp-report status")
    assert_eq(body, b"", "204 response body must be empty")

    # The structured log line should now be in the server's stdout log.
    # The server is launched with ``python3 -u`` (unbuffered) and the
    # handler calls ``print(..., flush=True)``, but give the OS a beat to
    # make the write visible to a separate file-reader process.
    log_path = log_dir / "server-test.log"
    log_text = ""
    for _ in range(20):
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        if "[csp_report]" in log_text:
            break
        time.sleep(0.05)
    assert "[csp_report]" in log_text, (
        "structured [csp_report] log line missing from server log "
        f"(log_path={log_path}, last 500 chars={log_text[-500:]!r})")
    assert "document=https://example.com/i/test" in log_text, (
        "log line missing the document-uri field")
    assert "blocked=https://evil.com/script.js" in log_text, (
        "log line missing the blocked-uri field")
    assert "directive=script-src" in log_text, (
        "log line missing the violated-directive field")

    # Unauthenticated → NO audit row.
    with open_db(data) as db:
        after = count_csp_audit_events(db)
    assert_eq(after, before,
              "unauthenticated report must NOT write an audit event")


def run_authenticated_legacy(base, data, token):
    """Phase 3: authenticated legacy report → 204 + log line + audit row."""
    with open_db(data) as db:
        before = count_csp_audit_events(db)

    status, body, _headers = http_request(
        base, "/api/csp-report",
        body=json.dumps(SAMPLE_LEGACY_REPORT),
        content_type="application/csp-report",
        token=token)
    assert_eq(status, 204,
              "authenticated legacy POST /api/csp-report status")

    with open_db(data) as db:
        after = count_csp_audit_events(db)
        rows = fetch_csp_audit_events(db)
    assert_eq(after, before + 1,
              "authenticated report must write exactly one audit event")

    row = rows[-1]
    assert row["user_id"], (
        f"audit event user_id must be set for authenticated report: {dict(row)}")
    assert_eq(row["action"], "csp.violation", "audit event action")
    assert_eq(row["target_type"], "csp", "audit event target_type")
    meta = json.loads(row["metadata_json"] or "{}")
    assert_eq(meta.get("violated_directive"), "script-src",
              "audit metadata violated_directive")
    assert_eq(meta.get("blocked_uri"), "https://evil.com/script.js",
              "audit metadata blocked_uri")
    assert_eq(meta.get("document_uri"), "https://example.com/i/test",
              "audit metadata document_uri")
    assert_eq(meta.get("source_file"), "https://example.com/i/test",
              "audit metadata source_file")
    assert_eq(int(meta.get("line_number", 0)), 42,
              "audit metadata line_number")
    assert_eq(int(meta.get("column_number", 0)), 1,
              "audit metadata column_number")


def run_reporting_api_shape(base, data, token):
    """Phase 4: Reporting-API array body → 204 + audit row with normalised fields."""
    with open_db(data) as db:
        before = count_csp_audit_events(db)

    status, body, _headers = http_request(
        base, "/api/csp-report",
        body=json.dumps(SAMPLE_REPORTING_API_BODY),
        content_type="application/reports+json",
        token=token)
    assert_eq(status, 204,
              "reporting-api POST /api/csp-report status")

    with open_db(data) as db:
        after = count_csp_audit_events(db)
        rows = fetch_csp_audit_events(db)
    assert_eq(after, before + 1,
              "reporting-api report must write one audit event")
    meta = json.loads(rows[-1]["metadata_json"] or "{}")
    assert_eq(meta.get("blocked_uri"), "https://evil.com/script.js",
              "reporting-api audit blocked_uri (normalised from blockedURL)")
    assert_eq(meta.get("violated_directive"), "script-src",
              "reporting-api audit violated_directive (normalised from effectiveDirective)")
    assert_eq(int(meta.get("line_number", 0)), 42,
              "reporting-api audit line_number (normalised from lineNumber)")


def run_rate_limit(base):
    """Phase 5: 60 requests in 60 seconds succeed; the 61st returns 429.

    Counting prior phases (against the same per-IP budget):
      Phase 2 (unauth legacy):       1 request
      Phase 3 (auth legacy):         1 request
      Phase 4 (reporting-api):       1 request
      Malformed-body phase (below):  1 request
                                      ─────
      Total already used:             4 requests
    So we have 56 remaining to hit 60, then the 61st must 429.
    """
    already_used = 4
    remaining = 60 - already_used
    for i in range(remaining):
        status, _body, _headers = http_request(
            base, "/api/csp-report",
            body=json.dumps(SAMPLE_LEGACY_REPORT),
            content_type="application/csp-report")
        if status != 204:
            raise AssertionError(
                f"rate-limit request {i + 1}/{remaining} (the "
                f"{already_used + i + 1}th overall) should succeed with 204, "
                f"got {status}")
    # The 61st overall request must now be rejected.
    status, body, _headers = http_request(
        base, "/api/csp-report",
        body=json.dumps(SAMPLE_LEGACY_REPORT),
        content_type="application/csp-report")
    assert_eq(status, 429,
              "61st request in the same minute must be rate-limited (429)")


def run_malformed_body(base):
    """Phase 6: a malformed JSON body still returns 204 — never 4xx/5xx,
    because the browser would retry on 5xx and amplify noise.

    NB: this MUST run BEFORE the rate-limit phase, because the rate-limit
    phase exhausts the 60/min budget and any subsequent request would
    return 429 (which is correct rate-limiting, not a malformed-body
    failure).
    """
    status, body, _headers = http_request(
        base, "/api/csp-report",
        body="this is not valid json",
        content_type="application/csp-report")
    assert_eq(status, 204,
              "malformed-body POST /api/csp-report must still return 204")


def run():
    # Use the inner tempdir created by ``app_server`` for BOTH the DB and
    # the server log file. The rate-limit test depends on a single shared
    # budget across phases, so the entire suite must run against one
    # server instance + one DB.
    env_override = {
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "EINVITE_REQUIRE_EMAIL_VERIFICATION": "0",
    }
    with app_server(extra_env=env_override) as (_proc, base, data):
        log_dir = data  # the server's working dir, contains server-test.log

        run_header_check(base)

        # Register + login to get a bearer token (DEV_AUTH_TOKENS=1 is
        # set by app_server, so the login response includes a token).
        http_json_request(base, "/api/auth/register", "POST",
                          {"email": EMAIL, "password": PASSWORD},
                          expected=201)
        _status, payload = http_json_request(
            base, "/api/auth/login", "POST",
            {"email": EMAIL, "password": PASSWORD},
            expected=201)
        token = payload.get("token")
        assert token, (
            f"login response missing bearer token (DEV_AUTH_TOKENS must "
            f"be enabled in the test env): {payload}")

        run_unauthenticated_legacy(base, data, log_dir)
        run_authenticated_legacy(base, data, token)
        run_reporting_api_shape(base, data, token)
        run_malformed_body(base)
        run_rate_limit(base)

    print("SECURITY_CSP_REPORT_TEST_PASSED")


# pytest-compatible entry point.
def test_csp_report():
    run()


if __name__ == "__main__":
    run()
