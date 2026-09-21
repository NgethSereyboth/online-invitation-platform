"""tests/analytics_privacy_test.py — v0.68.3 (ROADMAP Part 6 §6.7)

End-to-end test of the privacy controls:

Phase 1 — Host can disable analytics per invitation (POST /api/invitations/
          {id}/analytics/disable). After disable, ingestion silently
          accepts the batch but doesn't persist anything.
Phase 2 — Host can re-enable analytics (POST /disable with enabled:true).
Phase 3 — Host can purge all analytics data (DELETE /api/invitations/{id}/
          analytics). Subsequent GET /analytics shows empty analytics.
Phase 4 — Public privacy page at /privacy.html mentions the analytics
          section + the retention period + bilingual (EN+KH) labels.
Phase 5 — docs/analytics/PRIVACY.md + docs/analytics/EVENT-MODEL.md exist
          + contain the required sections.
Phase 6 — Non-host cannot disable/purge analytics (403 forbidden).
Phase 7 — Rate limits: spamming /disable 20 times → 429 after the 10th.

Runs against a real app server via tests/v14_test_utils.app_server.
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "python"))
sys.path.insert(0, str(ROOT))

from tests.v14_test_utils import app_server  # noqa: E402

USERNAME = "analytics-privacy@example.com"
USERNAME2 = "analytics-privacy-other@example.com"
PASSWORD = "Password123!"


def _post(base, path, body, headers=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        base + path, data=data, method="POST",
        headers={**({"Content-Type": "application/json"}), **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode() if isinstance(e, Exception) else b""


def _get(base, path, headers=None):
    req = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode() if isinstance(e, Exception) else b""


def _delete(base, path, headers=None):
    req = urllib.request.Request(base + path, method="DELETE", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode() if isinstance(e, Exception) else b""


def _register_and_login(base, email=USERNAME):
    s, b = _post(base, "/api/auth/register", {"email": email, "password": PASSWORD})
    assert s == 201, f"register failed: {s} {b}"
    s, b = _post(base, "/api/auth/login", {"email": email, "password": PASSWORD})
    assert s == 201, f"login failed: {s} {b}"
    token = json.loads(b).get("token")
    return {"Authorization": "Bearer " + token}


def _create_invitation(base, headers, slug):
    s, b = _post(base, "/api/invitations", {"slug": slug}, headers)
    assert s == 201, f"create invite failed: {s} {b}"
    return json.loads(b)["id"]


def _ingest(base, inv_id, sid, events):
    return _post(base, "/api/analytics/events", {
        "sessionId": sid, "invitationId": inv_id, "events": events,
    })


def _hex32(seed: int) -> str:
    return ("%032x" % seed).zfill(32)


def test_phase1_disable():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "priv-disable")
        # Seed some data.
        now = int(time.time() * 1000)
        s, _ = _ingest(base, inv_id, _hex32(1), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
        ])
        assert s == 204
        # Verify the data was persisted.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        a = json.loads(b)["analytics"]
        assert a["stats"]["totalViews"] >= 1
        # Disable analytics.
        s, b = _post(base, f"/api/invitations/{inv_id}/analytics/disable",
                     {"enabled": False}, headers)
        assert s == 200, f"disable failed: {s} {b!r}"
        d = json.loads(b)
        assert d["analyticsEnabled"] is False, f"expected analyticsEnabled=False, got {d}"
        # Ingest again — should silently accept but not persist.
        s, _ = _ingest(base, inv_id, _hex32(2), [
            {"type": "invitation.view", "ts": int(time.time() * 1000), "payload": {"viewport": "mobile"}},
        ])
        assert s == 204, f"ingest after disable should return 204 (silent), got {s}"
        # Verify the new event was NOT persisted.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        a = json.loads(b)["analytics"]
        assert a["stats"]["totalViews"] == 1, \
            f"expected totalViews=1 (post-disable ingest not persisted), got {a['stats']['totalViews']}"
        print("Phase 1 (disable + silent ingest) PASSED")


def test_phase2_reenable():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "priv-reenable")
        # Disable.
        s, b = _post(base, f"/api/invitations/{inv_id}/analytics/disable",
                     {"enabled": False}, headers)
        assert s == 200
        # Re-enable.
        s, b = _post(base, f"/api/invitations/{inv_id}/analytics/disable",
                     {"enabled": True}, headers)
        assert s == 200, f"reenable failed: {s} {b!r}"
        assert json.loads(b)["analyticsEnabled"] is True
        # Ingest should now persist.
        s, _ = _ingest(base, inv_id, _hex32(10), [
            {"type": "invitation.view", "ts": int(time.time() * 1000), "payload": {"viewport": "mobile"}},
        ])
        assert s == 204
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        a = json.loads(b)["analytics"]
        assert a["stats"]["totalViews"] == 1, \
            f"expected 1 view after re-enable, got {a['stats']['totalViews']}"
        print("Phase 2 (re-enable) PASSED")


def test_phase3_purge():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "priv-purge")
        # Seed data.
        now = int(time.time() * 1000)
        _ingest(base, inv_id, _hex32(20), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
            {"type": "invitation.rsvp.open", "ts": now, "payload": {}},
            {"type": "invitation.view.end", "ts": now, "payload": {"duration_ms": 1000, "max_scroll_pct": 30}},
        ])
        _ingest(base, inv_id, _hex32(21), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "desktop"}},
        ])
        # Verify data exists.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        a = json.loads(b)["analytics"]
        assert a["stats"]["totalViews"] >= 2
        # Purge.
        s, b = _delete(base, f"/api/invitations/{inv_id}/analytics", headers)
        assert s == 200, f"purge failed: {s} {b!r}"
        d = json.loads(b)
        assert d["ok"] is True
        assert d["sessionsDeleted"] >= 2, f"expected >=2 sessions deleted, got {d}"
        assert d["eventsDeleted"] >= 3, f"expected >=3 events deleted, got {d}"
        # Verify data is gone.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        a = json.loads(b)["analytics"]
        assert a["stats"]["totalViews"] == 0, \
            f"expected totalViews=0 after purge, got {a['stats']['totalViews']}"
        print("Phase 3 (purge) PASSED")


def test_phase4_public_privacy_page():
    with app_server() as (proc, base, _):
        s, b = _get(base, "/privacy.html")
        assert s == 200, f"privacy page failed: {s} {b!r}"
        text = b.decode("utf-8")
        assert "Creator analytics" in text, "privacy page should mention Creator analytics"
        assert "EINVITE_ANALYTICS_RETENTION_DAYS" in text, \
            "privacy page should mention retention env var"
        assert "sessionStorage" in text, "privacy page should mention sessionStorage"
        assert "first-party" in text or "first party" in text, \
            "privacy page should mention first-party"
        # Bilingual (Khmer section present).
        assert "ភាសាខ្មែរ" in text, "privacy page should have Khmer (ភាសាខ្មែរ) section"
        print("Phase 4 (public privacy page) PASSED")


def test_phase5_docs():
    privacy_doc = ROOT / "docs" / "analytics" / "PRIVACY.md"
    event_doc = ROOT / "docs" / "analytics" / "EVENT-MODEL.md"
    assert privacy_doc.is_file(), f"PRIVACY.md missing at {privacy_doc}"
    assert event_doc.is_file(), f"EVENT-MODEL.md missing at {event_doc}"
    p = privacy_doc.read_text(encoding="utf-8")
    assert "Retention" in p, "PRIVACY.md should have a retention section"
    assert "EINVITE_ANALYTICS_RETENTION_DAYS" in p
    assert "GDPR" in p, "PRIVACY.md should mention GDPR"
    assert "PECR" in p, "PRIVACY.md should mention PECR (no analytics cookies)"
    assert "Bilingual" in p, "PRIVACY.md should document bilingual labels"
    assert "ភ្ញៀវ" in p or "ស្ថិតិ" in p, "PRIVACY.md should have Khmer strings"
    e = event_doc.read_text(encoding="utf-8")
    assert "analytics_sessions" in e
    assert "analytics_events" in e
    assert "analytics_summary_daily" in e
    assert "invitation.view" in e and "invitation.view.end" in e
    assert "invitation.rsvp.abandon" in e and "invitation.gift.claim" in e
    # All 11 event types listed.
    expected = [
        "invitation.view", "invitation.view.end", "invitation.gallery.open",
        "invitation.rsvp.open", "invitation.rsvp.submit", "invitation.rsvp.abandon",
        "invitation.link.click", "invitation.signup.claim", "invitation.poll.vote",
        "invitation.album.upload", "invitation.gift.claim",
    ]
    for et in expected:
        assert et in e, f"EVENT-MODEL.md missing event type {et}"
    print("Phase 5 (docs) PASSED")


def test_phase6_non_host_forbidden():
    with app_server() as (proc, base, _):
        # Host 1 creates an invitation.
        host1 = _register_and_login(base, USERNAME)
        inv_id = _create_invitation(base, host1, "priv-nonhost")
        # Host 2 (different account) tries to disable/purge.
        host2 = _register_and_login(base, USERNAME2)
        s, b = _post(base, f"/api/invitations/{inv_id}/analytics/disable",
                     {"enabled": False}, host2)
        assert s == 403, f"non-host disable should be 403, got {s} {b!r}"
        s, b = _delete(base, f"/api/invitations/{inv_id}/analytics", host2)
        assert s == 403, f"non-host purge should be 403, got {s} {b!r}"
        print("Phase 6 (non-host forbidden) PASSED")


def test_phase7_disable_rate_limit():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "priv-ratelimit")
        rejected = 0
        accepted = 0
        for _ in range(20):
            s, b = _post(base, f"/api/invitations/{inv_id}/analytics/disable",
                         {"enabled": True}, headers)
            if s == 200:
                accepted += 1
            elif s == 429:
                rejected += 1
        assert accepted == 10, f"expected 10 accepted (rate limit), got {accepted}"
        assert rejected == 10, f"expected 10 rejected, got {rejected}"
        print(f"Phase 7 (rate limit) PASSED — accepted={accepted} rejected={rejected}")


def main():
    os.environ.setdefault("EINVITE_ALLOW_NO_SCANNER", "1")
    test_phase5_docs()
    test_phase4_public_privacy_page()
    test_phase1_disable()
    test_phase2_reenable()
    test_phase3_purge()
    test_phase6_non_host_forbidden()
    test_phase7_disable_rate_limit()
    print("\nANALYTICS_PRIVACY_TEST_PASSED")


if __name__ == "__main__":
    main()
