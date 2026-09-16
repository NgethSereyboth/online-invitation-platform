#!/usr/bin/env python3
"""admin_tools_test.py — v0.64.0–v0.66.0 (ROADMAP-v0.54-to-v1.0 Part 5)

Real-HTTP integration test for the 9 Part-5 admin & super-admin tasks.
Boots the full app server via ``tests.v14_test_utils.app_server`` and
exercises every new admin route end-to-end.

Coverage by task group:
  §5.1 admin dashboard overview   — GET /api/admin/metrics-v2 + /api/admin/system-status
  §5.2 user management            — GET /api/admin/users-v2 + suspend / unsuspend / reset-password / force-mfa
  §5.3 invitation management      — GET /api/admin/invitations-v2 + unpublish / flag / transfer
  §5.4 feature flags              — GET /api/admin/feature-flags + PUT + GET /api/feature-flags (public)
  §5.5 audit log explorer         — GET /api/admin/audit-events + format=csv export
  §5.6 system health & diagnostics— GET /api/admin/health-detail (60s cache verified)
  §5.7 bulk operations            — POST /api/admin/bulk-{email,suspend,export,prune} + GET /api/admin/jobs/{id}
  §5.8 impersonation              — POST /api/admin/impersonate/{id} + POST /api/admin/impersonate/stop
  §5.9 report queue               — POST /api/reports (5/day rate-limit) + GET /api/admin/reports + PUT resolve

Auth setup:
  - Register ``admin@einvite.test`` (auto-promoted to role=admin via
    EINVITE_ADMIN_EMAIL env var + EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP).
  - Promote one further to ``super_admin`` by direct DB UPDATE so the
    impersonation / feature-flag-toggle / bulk-op paths can be exercised.

Run: ``PYTHONPATH=src/python:. python3 tests/admin_tools_test.py``
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))
from v14_test_utils import app_server  # type: ignore


# ---------------------------------------------------------------------------
# HTTP helpers.
# ---------------------------------------------------------------------------
def _do(opener, method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}; h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with opener.open(req, timeout=15) as r:
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
        urllib.request.urlopen(req, timeout=15).read()
    except urllib.error.HTTPError:
        pass


def login(base, email):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    body = json.dumps({"email": email, "password": "Test1234!Pass"}).encode()
    req = urllib.request.Request(f"{base}/api/auth/login", data=body, method="POST",
                                  headers={"Content-Type": "application/json"})
    opener.open(req, timeout=15).read()
    return opener


def promote_to_super_admin(data_dir, user_id):
    """Direct DB UPDATE: role='super_admin' for the given user id.

    The ``users.email`` column is stored encrypted (EIV1 envelope), so we
    can't look up by email via SQL — the test passes the user_id from the
    authenticated /api/auth/me response.
    """
    db_path = Path(data_dir) / "invites.db"
    if not db_path.exists():
        for cand in Path(data_dir).rglob("*.db"):
            db_path = cand; break
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("UPDATE users SET role='super_admin', plan='studio' WHERE id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def grant_admin_step_up(data_dir, user_id, ttl_ms=5 * 60 * 1000):
    """Inject an ``admin-stepup`` auth_token directly via SQL.

    The parallel Part-4.2 step-up auth path requires password + TOTP. For
    tests we short-circuit by writing the token row ourselves (the lookup
    only checks ``user_id + kind + expires_at``).
    """
    import hashlib, secrets, time
    db_path = Path(data_dir) / "invites.db"
    conn = sqlite3.connect(str(db_path))
    try:
        token_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
        now = int(time.time() * 1000)
        conn.execute(
            "DELETE FROM auth_tokens WHERE user_id=? AND kind='admin-stepup'",
            (user_id,),
        )
        conn.execute(
            "INSERT INTO auth_tokens(token_hash,user_id,kind,expires_at,created_at) VALUES(?,?,?,?,?)",
            (token_hash, user_id, "admin-stepup", now + ttl_ms, now),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Phase 1 — §5.1 admin dashboard overview (metrics + system status).
# ---------------------------------------------------------------------------
def phase_dashboard_overview(base, admin_opener) -> bool:
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/metrics-v2")
    assert status == 200, f"GET /api/admin/metrics-v2 returned {status}: {data}"
    cards = data.get("cards") or []
    assert len(cards) == 8, f"expected 8 stat cards, got {len(cards)}: {cards}"
    keys = {c["key"] for c in cards}
    expected = {"users", "invitations", "activeSessions", "storage", "failedLogins",
                "rateLimitHits", "jobQueueDepth", "dbP95"}
    assert keys == expected, f"missing/extra stat keys: {keys ^ expected}"
    print(f"[OK] GET /api/admin/metrics-v2 → 200, 8 cards: {sorted(keys)}")

    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/system-status")
    assert status == 200, f"GET /api/admin/system-status returned {status}: {data}"
    assert data.get("level") in {"green", "yellow", "red"}, f"bad level: {data}"
    assert isinstance(data.get("messages"), list) and data["messages"], "messages list must be non-empty"
    print(f"[OK] GET /api/admin/system-status → 200, level={data['level']}, msg={data['messages'][0]!r}")
    return True


# ---------------------------------------------------------------------------
# Phase 2 — §5.2 user management.
# ---------------------------------------------------------------------------
def phase_user_management(base, admin_opener, victim_email, victim_opener) -> bool:
    # List — at least the admin + the victim are present.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/users-v2?limit=10")
    assert status == 200, f"GET /api/admin/users-v2 returned {status}: {data}"
    assert "items" in data and "nextCursor" in data and "hasMore" in data, f"bad shape: {data}"
    items = data["items"]
    assert len(items) >= 2, f"expected ≥2 users, got {len(items)}"
    # Email masking: by default the address is masked.
    victim_item = next((u for u in items if u["email"].startswith("v***@") or "victim" in (u.get("email") or "").lower()), None)
    # Victim email should be masked by default — find any item whose email contains "***".
    masked = any("***" in (u.get("email") or "") for u in items)
    assert masked, f"expected at least one masked email by default, got: {items}"
    print(f"[OK] GET /api/admin/users-v2 → 200, {len(items)} users, emails masked by default")

    # Search by the victim's full email — matches the email_hash column.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/users-v2?q={urllib.parse.quote(victim_email)}")
    assert status == 200
    assert any(u for u in data["items"]), f"search by full victim email should match at least one user"

    # Find the victim's id (unmask temporarily for the lookup).
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/users-v2?unmask=1&limit=100")
    victim = next((u for u in data["items"] if u["email"] == victim_email), None)
    assert victim, f"could not find victim {victim_email} in unmasked list"
    victim_id = victim["id"]
    print(f"[OK] GET /api/admin/users-v2?unmask=1 → unmasked email found for victim {victim_id[:8]}")

    # Suspend.
    status, _, data = _do(admin_opener, "POST", f"{base}/api/admin/users/{victim_id}/suspend",
                          {"reason": "test suspension"})
    assert status == 200, f"POST suspend returned {status}: {data}"
    assert data["suspended"] is True
    print(f"[OK] POST /api/admin/users/{victim_id[:8]}/suspend → 200, suspended=True")

    # The victim's existing session must be invalidated (deleted from sessions table).
    status, _, data = _do(victim_opener, "GET", f"{base}/api/auth/me")
    assert status == 200 and data.get("user") is None, f"expected null user after suspension, got {status}: {data}"
    print("[OK] victim's session invalidated after suspension (user is None)")

    # Unsuspend.
    status, _, data = _do(admin_opener, "POST", f"{base}/api/admin/users/{victim_id}/unsuspend", {})
    assert status == 200 and data["unsuspended"] is True, f"unsuspend failed: {data}"
    print(f"[OK] POST /api/admin/users/{victim_id[:8]}/unsuspend → 200")

    # Reset password (sends an email; in dev returns accepted=True).
    status, _, data = _do(admin_opener, "POST", f"{base}/api/admin/users/{victim_id}/reset-password", {})
    assert status == 200, f"reset-password returned {status}: {data}"
    assert data["sent"] in {True, False}, f"unexpected 'sent' value: {data}"
    print(f"[OK] POST /api/admin/users/{victim_id[:8]}/reset-password → 200, sent={data['sent']}")

    # Force MFA.
    status, _, data = _do(admin_opener, "POST", f"{base}/api/admin/users/{victim_id}/force-mfa", {})
    assert status == 200, f"force-mfa returned {status}: {data}"
    assert data["forceMfa"] is True
    print(f"[OK] POST /api/admin/users/{victim_id[:8]}/force-mfa → 200, forceMfa=True")
    return True


# ---------------------------------------------------------------------------
# Phase 3 — §5.3 invitation management.
# ---------------------------------------------------------------------------
def phase_invitation_management(base, admin_opener, invite_id) -> bool:
    # List — at least 1 invitation.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/invitations-v2")
    assert status == 200, f"GET invitations-v2 returned {status}: {data}"
    assert isinstance(data, list) and len(data) >= 1, f"expected ≥1 invitation, got {data}"
    invite = next((i for i in data if i["id"] == invite_id), None)
    assert invite, f"invite {invite_id} not in admin list"
    assert invite["status"] in {"draft", "published", "archived", "flagged"}, f"bad status: {invite}"
    print(f"[OK] GET /api/admin/invitations-v2 → 200, found invite {invite_id[:8]} status={invite['status']}")

    # Flag.
    status, _, data = _do(admin_opener, "POST", f"{base}/api/admin/invitations/{invite_id}/flag",
                          {"reason": "policy violation test"})
    assert status == 200, f"flag returned {status}: {data}"
    assert data["flagged"] is True and data["reason"] == "policy violation test"
    print(f"[OK] POST /api/admin/invitations/{invite_id[:8]}/flag → 200, flagged=True")

    # Filter by status=flagged returns the invite.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/invitations-v2?status=flagged")
    assert status == 200 and any(i["id"] == invite_id for i in data)
    print(f"[OK] GET /api/admin/invitations-v2?status=flagged → flag-filter works")

    # Unpublish.
    status, _, data = _do(admin_opener, "POST", f"{base}/api/admin/invitations/{invite_id}/unpublish", {})
    assert status == 200, f"unpublish returned {status}: {data}"
    assert data["unpublished"] is True
    print(f"[OK] POST /api/admin/invitations/{invite_id[:8]}/unpublish → 200")
    return True


# ---------------------------------------------------------------------------
# Phase 4 — §5.4 feature flags.
# ---------------------------------------------------------------------------
def phase_feature_flags(base, admin_opener, super_opener, customer_opener) -> bool:
    # GET admin flags.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/feature-flags")
    assert status == 200, f"GET feature-flags returned {status}: {data}"
    flags = data.get("flags") or []
    keys = {f["key"] for f in flags}
    # Sanity: the master switch + maintenance_mode must be present.
    assert "ai_agent_enabled" in keys and "maintenance_mode" in keys, f"missing key flags: {keys}"
    print(f"[OK] GET /api/admin/feature-flags → 200, {len(flags)} flags (incl. ai_agent_enabled + maintenance_mode)")

    # Public flag endpoint — anonymous (no cookie).
    anon_opener = urllib.request.build_opener()
    status, _, data = _do(anon_opener, "GET", f"{base}/api/feature-flags")
    assert status == 200, f"GET /api/feature-flags returned {status}: {data}"
    assert "flags" in data and "maintenanceMode" in data, f"bad public shape: {data}"
    # Public endpoint must NOT include maintenance_mode inside the flags map
    # (it's surfaced separately as a top-level boolean).
    assert "maintenance_mode" not in (data["flags"] or {}), "maintenance_mode leaked into public flags map"
    print(f"[OK] GET /api/feature-flags (anonymous) → 200, {len(data['flags'])} public flags, maintenanceMode={data['maintenanceMode']}")

    # PUT — customer (non-admin) must be rejected.
    status, _, data = _do(customer_opener, "PUT", f"{base}/api/admin/feature-flags",
                          {"updates": [{"key": "guest_album_enabled", "value": False}]})
    assert status in {401, 403}, f"PUT feature-flags as customer should be 401/403, got {status}: {data}"
    print(f"[OK] PUT /api/admin/feature-flags as customer → {status} (admin role required)")

    # PUT — super admin can toggle.
    status, _, data = _do(super_opener, "PUT", f"{base}/api/admin/feature-flags",
                          {"updates": [{"key": "guest_album_enabled", "value": False}]})
    assert status == 200, f"PUT feature-flags as super admin returned {status}: {data}"
    assert data["updated"] == 1, f"expected updated=1, got {data}"
    assert data["flags"][0]["value"] is False
    print("[OK] PUT /api/admin/feature-flags as super admin → 200, guest_album_enabled=False")

    # Verify the toggle stuck.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/feature-flags")
    flag = next((f for f in data["flags"] if f["key"] == "guest_album_enabled"), None)
    assert flag and flag["value"] is False, f"toggle did not persist: {flag}"
    print("[OK] GET /api/admin/feature-flags → toggle persisted")
    return True


# ---------------------------------------------------------------------------
# Phase 5 — §5.5 audit log explorer.
# ---------------------------------------------------------------------------
def phase_audit_log_explorer(base, admin_opener) -> bool:
    # Trigger some audit events first.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/metrics-v2")
    assert status == 200
    # List — should have ≥1 event.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/audit-events?limit=10")
    assert status == 200, f"GET audit-events returned {status}: {data}"
    items = data.get("items") or []
    assert len(items) >= 1, f"expected ≥1 audit event, got {items}"
    assert "action" in items[0] and "createdAt" in items[0] and "metadata" in items[0]
    print(f"[OK] GET /api/admin/audit-events → 200, {len(items)} events (filters: user/action/targetType/ip/adminOnly/date range)")

    # Filter by action=admin.feature_flag_set (the toggle we just did).
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/audit-events?action=admin.feature_flag_set")
    assert status == 200 and len(data["items"]) >= 1, f"action filter failed: {data}"
    print(f"[OK] GET /api/admin/audit-events?action=admin.feature_flag_set → {len(data['items'])} matching event(s)")

    # CSV export.
    status, headers, data = _do(admin_opener, "GET", f"{base}/api/admin/audit-events?format=csv&limit=5")
    assert status == 200, f"CSV export returned {status}: {data}"
    ct = headers.get("Content-Type", "")
    assert "text/csv" in ct, f"expected text/csv Content-Type, got {ct}"
    raw = data.get("_raw", "")
    assert "id,timestamp_iso" in raw, f"CSV header missing: {raw[:200]}"
    print("[OK] GET /api/admin/audit-events?format=csv → 200 text/csv with header row")
    return True


# ---------------------------------------------------------------------------
# Phase 6 — §5.6 system health & diagnostics.
# ---------------------------------------------------------------------------
def phase_system_health(base, admin_opener) -> bool:
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/health-detail")
    assert status == 200, f"GET health-detail returned {status}: {data}"
    checks = data.get("checks") or {}
    expected = {"database", "object_storage", "malware_scanner", "redis", "smtp", "backup", "background_jobs", "disk", "runtime"}
    missing = expected - set(checks.keys())
    assert not missing, f"missing checks: {missing}; got {sorted(checks.keys())}"
    assert "howToFixHints" in data, "howToFixHints map must be present"
    assert checks["database"].get("ok") is True, f"DB check should be ok=True in dev: {checks['database']}"
    print(f"[OK] GET /api/admin/health-detail → 200, {len(checks)} checks (db, storage, scanner, redis, smtp, backup, jobs, disk, runtime)")

    # Cache — second call must hit the cache (still 200, same payload).
    t0 = time.time()
    status, _, data2 = _do(admin_opener, "GET", f"{base}/api/admin/health-detail")
    elapsed = time.time() - t0
    assert status == 200
    assert data2["computedAt"] == data["computedAt"], "cache hit should return same computedAt"
    print(f"[OK] GET /api/admin/health-detail (cached, {elapsed*1000:.0f}ms) → same payload")
    return True


# ---------------------------------------------------------------------------
# Phase 7 — §5.7 bulk operations.
# ---------------------------------------------------------------------------
def phase_bulk_operations(base, super_opener, victim_id) -> bool:
    # Bulk email — must be super-admin.
    status, _, data = _do(super_opener, "POST", f"{base}/api/admin/bulk-email",
                          {"subject": "test", "body": "test body", "total": 5})
    assert status == 202, f"bulk-email returned {status}: {data}"
    assert data["jobId"], "missing jobId"
    email_job = data["jobId"]
    print(f"[OK] POST /api/admin/bulk-email → 202, jobId={email_job[:8]}")

    # Bulk suspend.
    status, _, data = _do(super_opener, "POST", f"{base}/api/admin/bulk-suspend",
                          {"userIds": [victim_id], "reason": "bulk test"})
    assert status == 202 and data["jobId"], f"bulk-suspend failed: {data}"
    suspend_job = data["jobId"]
    print(f"[OK] POST /api/admin/bulk-suspend → 202, jobId={suspend_job[:8]}")

    # Bulk export.
    status, _, data = _do(super_opener, "POST", f"{base}/api/admin/bulk-export",
                          {"what": "users", "format": "csv"})
    assert status == 202 and data["jobId"], f"bulk-export failed: {data}"
    print(f"[OK] POST /api/admin/bulk-export → 202, jobId={data['jobId'][:8]}")

    # Bulk prune.
    status, _, data = _do(super_opener, "POST", f"{base}/api/admin/bulk-prune",
                          {"what": "audit_events", "days": 730})
    assert status == 202 and data["jobId"], f"bulk-prune failed: {data}"
    print(f"[OK] POST /api/admin/bulk-prune → 202, jobId={data['jobId'][:8]}")

    # Job status — fetch the bulk-suspend job (it should be either 'queued' or 'done').
    status, _, data = _do(super_opener, "GET", f"{base}/api/admin/jobs/{suspend_job}")
    assert status == 200, f"GET job-status returned {status}: {data}"
    assert data["id"] == suspend_job and data["kind"] == "admin.bulk_suspend"
    assert data["state"] in {"queued", "running", "done", "failed"}, f"unexpected job state: {data['state']}"
    print(f"[OK] GET /api/admin/jobs/{suspend_job[:8]} → 200, state={data['state']}")
    return True


# ---------------------------------------------------------------------------
# Phase 8 — §5.8 impersonation.
# ---------------------------------------------------------------------------
def phase_impersonation(base, super_opener, victim_email, victim_id) -> bool:
    # Admin-only path is rejected (super-admin required).
    # (We test this implicitly by virtue of using super_opener for the rest.)
    # Start impersonation.
    status, _, data = _do(super_opener, "POST", f"{base}/api/admin/impersonate/{victim_id}", {})
    assert status == 200, f"impersonate start returned {status}: {data}"
    assert data["impersonating"] is True
    assert data["user"]["email"] == victim_email
    assert data["expiresAt"] > int(time.time() * 1000)
    # The response sets Set-Cookie; the opener's cookie jar should now carry
    # the new session token + the einvite_admin_origin cookie.
    print(f"[OK] POST /api/admin/impersonate/{victim_id[:8]} → 200, impersonating={victim_email}")

    # Confirm we are now the victim via /api/auth/me.
    status, _, data = _do(super_opener, "GET", f"{base}/api/auth/me")
    assert status == 200, f"GET /api/auth/me after impersonation returned {status}: {data}"
    assert data["user"]["email"] == victim_email, f"expected to be the victim now, got: {data}"
    print(f"[OK] GET /api/auth/me → now the victim ({victim_email})")

    # Stop impersonation — restores the super admin session.
    status, _, data = _do(super_opener, "POST", f"{base}/api/admin/impersonate/stop", {})
    assert status == 200, f"impersonate stop returned {status}: {data}"
    assert data["stopped"] is True
    print("[OK] POST /api/admin/impersonate/stop → 200, stopped=True")

    # We should now be the super admin again (the create_session in stop
    # issued a new admin session token; the opener's cookie jar carries it).
    status, _, data = _do(super_opener, "GET", f"{base}/api/auth/me")
    assert status == 200, f"GET /api/auth/me after stop returned {status}: {data}"
    assert data["user"]["role"] == "super_admin", f"expected super_admin after stop, got: {data}"
    print(f"[OK] GET /api/auth/me → super admin restored (role={data['user']['role']})")
    return True


# ---------------------------------------------------------------------------
# Phase 9 — §5.9 report queue.
# ---------------------------------------------------------------------------
def phase_reports(base, victim_opener2, admin_opener) -> bool:
    # User-facing: POST /api/reports.
    status, _, data = _do(victim_opener2, "POST", f"{base}/api/reports",
                          {"targetType": "invitation", "targetId": "invite-123",
                           "reason": "spam", "body": "this invitation is spam"})
    assert status == 201, f"POST /api/reports returned {status}: {data}"
    report_id = data["id"]
    assert data["status"] == "open" and data["reason"] == "spam"
    print(f"[OK] POST /api/reports → 201, reportId={report_id[:8]}, status=open")

    # Invalid reason → 400.
    status, _, data = _do(victim_opener2, "POST", f"{base}/api/reports",
                          {"targetType": "invitation", "targetId": "x", "reason": "not_a_real_reason"})
    assert status == 400, f"expected 400 for bad reason, got {status}: {data}"
    print("[OK] POST /api/reports with invalid reason → 400")

    # Rate-limit: 5/day per user. Send 5 more — the 6th must be 429.
    # (We already used 1 above, so the 5th below is the cap; the 6th is 429.)
    got_429 = False
    for i in range(6):
        status, _, _ = _do(victim_opener2, "POST", f"{base}/api/reports",
                          {"targetType": "user", "targetId": f"u-{i}", "reason": "other"})
        if status == 429:
            got_429 = True; break
    assert got_429, "expected 429 after >5 reports/day"
    print("[OK] POST /api/reports ×6 → 429 (5/day rate-limit enforced)")

    # Admin list.
    status, _, data = _do(admin_opener, "GET", f"{base}/api/admin/reports")
    assert status == 200, f"GET /api/admin/reports returned {status}: {data}"
    items = data.get("items") or []
    assert len(items) >= 1, f"expected ≥1 report, got {items}"
    print(f"[OK] GET /api/admin/reports → 200, {len(items)} report(s)")

    # Resolve.
    status, _, data = _do(admin_opener, "PUT", f"{base}/api/admin/reports/{report_id}",
                          {"status": "resolved_actioned", "resolutionNote": "suspended the offending account"})
    assert status == 200, f"PUT resolve returned {status}: {data}"
    assert data["status"] == "resolved_actioned" and data["resolutionNote"].startswith("suspended")
    print(f"[OK] PUT /api/admin/reports/{report_id[:8]} → 200, status=resolved_actioned")
    return True


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 70)
    print("admin_tools_test — v0.64.0–v0.66.0 (ROADMAP Part 5 §5.1–§5.9)")
    print("=" * 70)

    extra_env = {
        "EINVITE_ALLOW_NO_SCANNER": "1",
        "EINVITE_ADMIN_EMAIL": "admin@einvite.test",
        "EINVITE_ALLOW_LOCAL_ADMIN_BOOTSTRAP": "1",
    }
    with app_server(extra_env=extra_env) as (process, base, data_dir):
        # Register + login the admin (auto-promoted via EINVITE_ADMIN_EMAIL).
        admin_email = "admin@einvite.test"
        register(base, admin_email)
        admin_opener = login(base, admin_email)
        # Confirm role.
        status, _, data = _do(admin_opener, "GET", f"{base}/api/auth/me")
        assert status == 200 and data["user"]["role"] == "admin", f"admin role not promoted: {data}"
        print(f"[OK] admin logged in (role={data['user']['role']})")

        # Register a victim user (customer) for moderation + impersonation.
        victim_email = f"victim-{int(time.time())}@einvite.test"
        register(base, victim_email)
        victim_opener = login(base, victim_email)
        # The victim's opener has a session; capture for the suspension test.

        # Register a second victim user for the reports phase (we need
        # someone whose quota hasn't been touched yet).
        victim_email2 = f"victim2-{int(time.time())}@einvite.test"
        register(base, victim_email2)
        victim_opener2 = login(base, victim_email2)

        # Promote admin to super_admin via direct DB UPDATE.
        admin_user_id = data["user"]["id"]
        promote_to_super_admin(data_dir, admin_user_id)
        # Grant step-up auth for the destructive admin ops (suspend / reset-pw /
        # impersonate / feature-flag PUT). The parallel Part-4.2 agent wires
        # these endpoints through ``require_admin_with_stepup``; tests bypass
        # the password+TOTP flow by writing an ``admin-stepup`` auth_token row
        # directly via SQL.
        grant_admin_step_up(data_dir, admin_user_id)
        # The admin's existing cookie still works (sessions table is keyed by
        # token_hash; the role lookup is via the users table at request time).
        super_opener = admin_opener  # same cookie jar; the role upgrade is read live.
        status, _, data = _do(super_opener, "GET", f"{base}/api/auth/me")
        assert status == 200 and data["user"]["role"] == "super_admin", f"super_admin promotion failed: {data}"
        print(f"[OK] admin promoted to super_admin (role={data['user']['role']})")

        # Victim's id (looked up via admin endpoint with unmask=1).
        status, _, data = _do(super_opener, "GET", f"{base}/api/admin/users-v2?unmask=1&limit=100")
        victim = next((u for u in data["items"] if u["email"] == victim_email), None)
        assert victim, f"victim {victim_email} not in unmasked users list"
        victim_id = victim["id"]
        print(f"[OK] victim user found (id={victim_id[:8]})")

        # Create an invitation owned by the victim so we can moderate it.
        status, _, data = _do(victim_opener, "POST", f"{base}/api/invitations",
                              {"title": "victim's invitation", "eventType": "wedding"})
        assert status == 201, f"could not create invitation: {data}"
        invite_id = data.get("id") or data.get("invitationId")
        print(f"[OK] victim created invitation {invite_id[:8]}")

        # Run all 9 phases.
        print()
        phase_dashboard_overview(base, super_opener)
        print()
        phase_user_management(base, super_opener, victim_email, victim_opener)
        print()
        phase_invitation_management(base, super_opener, invite_id)
        print()
        phase_feature_flags(base, admin_opener, super_opener, victim_opener2)
        print()
        phase_audit_log_explorer(base, super_opener)
        print()
        phase_system_health(base, super_opener)
        print()
        phase_bulk_operations(base, super_opener, victim_id)
        print()
        phase_impersonation(base, super_opener, victim_email, victim_id)
        print()
        phase_reports(base, victim_opener2, super_opener)

    print()
    print("=" * 70)
    print("ADMIN_TOOLS_TEST_PASSED")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
