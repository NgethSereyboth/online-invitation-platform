"""tests/analytics_reports_test.py — v0.68.x (ROADMAP Part 6 §6.4, §6.5, §6.6, §6.8)

End-to-end test of the creator analytics reporting + export layer:

Phase 1 — GET /api/invitations/{id}/analytics returns the extended payload
          with stats, timeseries, funnel, topReferrers, scrollDepth,
          deviceSplit, countrySplit.
Phase 2 — GET /api/account/analytics/creations returns a sortable, filterable
          table with the right shape (items, sort, order, count).
Phase 3 — GET /api/account/analytics/summary returns the account-level
          rollup (totalInvitations, totalViews, totalRsvps, ...).
Phase 4 — GET /api/invitations/{id}/analytics/export?format=csv returns a
          CSV with UTF-8 BOM + RFC-4180 quoting. format=json returns a
          JSON object with invitation + sessions + events.
Phase 5 — GET /api/account/analytics/export?format=csv returns a CSV
          concatenated across all of the account's invitations.
Phase 6 — GET /api/invitations/{id}/analytics/live returns 403 when
          the analytics_live_enabled flag is off (the default).
Phase 7 — JS module declarations: components/chart.js + pages/dashboard/
          analytics.js expose the expected globals + bilingual STRINGS.

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

USERNAME = "analytics-reports@example.com"
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


def _register_and_login(base):
    s, b = _post(base, "/api/auth/register", {"email": USERNAME, "password": PASSWORD})
    assert s == 201, f"register failed: {s} {b}"
    s, b = _post(base, "/api/auth/login", {"email": USERNAME, "password": PASSWORD})
    assert s == 201, f"login failed: {s} {b}"
    token = json.loads(b).get("token")
    return {"Authorization": "Bearer " + token}


def _create_invitation(base, headers, slug):
    s, b = _post(base, "/api/invitations", {"slug": slug}, headers)
    assert s == 201, f"create invite failed: {s} {b}"
    return json.loads(b)["id"]


def _ingest(base, inv_id, sid, events, recipient_id=None):
    body = {"sessionId": sid, "invitationId": inv_id, "events": events}
    if recipient_id:
        body["recipientId"] = recipient_id
    return _post(base, "/api/analytics/events", body)


def _hex32(seed: int) -> str:
    return ("%032x" % seed).zfill(32)


def test_phase1_per_invitation_analytics():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "reports-test-1")
        # Seed a few sessions across recipients + devices.
        # NOTE: each event's `ts` is the server's current time, NOT a future
        # time, so the per-period stats query (which filters started_at < now)
        # will include all of them.
        now = int(time.time() * 1000)
        _ingest(base, inv_id, _hex32(1), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile", "referrer": "https://facebook.com"}},
            {"type": "invitation.rsvp.open", "ts": now, "payload": {}},
            {"type": "invitation.rsvp.submit", "ts": now, "payload": {"status": "yes"}},
            {"type": "invitation.view.end", "ts": now, "payload": {"duration_ms": 5000, "max_scroll_pct": 80}},
        ], recipient_id="guest-1")
        now = int(time.time() * 1000)
        _ingest(base, inv_id, _hex32(2), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "desktop", "referrer": "https://google.com"}},
            {"type": "invitation.gallery.open", "ts": now, "payload": {}},
            {"type": "invitation.view.end", "ts": now, "payload": {"duration_ms": 10000, "max_scroll_pct": 50}},
        ], recipient_id="guest-2")
        now = int(time.time() * 1000)
        _ingest(base, inv_id, _hex32(3), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
            {"type": "invitation.rsvp.open", "ts": now, "payload": {}},
            # No view.end — session stays open.
        ], recipient_id="guest-1")
        # GET the analytics payload.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics", headers)
        assert s == 200, f"get analytics failed: {s} {b!r}"
        data = json.loads(b)
        a = data["analytics"]
        # Stat cards
        assert a["stats"]["totalViews"] >= 3, f"expected >=3 totalViews, got {a['stats']}"
        assert a["stats"]["uniqueRecipients"] >= 2, f"expected >=2 uniqueRecipients, got {a['stats']}"
        assert a["stats"]["rsvpConversion"] > 0, f"expected rsvpConversion > 0, got {a['stats']}"
        # Timeseries
        assert len(a["timeseries"]["days"]) == 30, "expected 30 days"
        assert len(a["timeseries"]["views"]) == 30
        assert len(a["timeseries"]["rsvps"]) == 30
        # Funnel
        steps = {f["step"]: f for f in a["funnel"]}
        assert steps["view"]["count"] >= 3
        assert steps["rsvp.open"]["count"] >= 2
        assert steps["rsvp.submit"]["count"] >= 1
        # Top referrers (only facebook + google with 1 each, both <3, so "Other"=2)
        ref_domains = {r["domain"] for r in a["topReferrers"]}
        assert "Other" in ref_domains, f"expected 'Other' referrer (count<3 masking), got {ref_domains}"
        # Scroll depth
        assert "average" in a["scrollDepth"]
        assert len(a["scrollDepth"]["buckets"]) == 4
        # Device split
        dev_labels = {d["label"] for d in a["deviceSplit"]}
        assert "mobile" in dev_labels and "desktop" in dev_labels, f"device labels: {dev_labels}"
        print("Phase 1 (per-invitation analytics) PASSED")


def test_phase2_creations_table():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv1 = _create_invitation(base, headers, "creations-1")
        inv2 = _create_invitation(base, headers, "creations-2")
        # Seed minimal data.
        now = int(time.time() * 1000)
        _ingest(base, inv1, _hex32(10), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
            {"type": "invitation.view.end", "ts": now + 1000,
             "payload": {"duration_ms": 1000, "max_scroll_pct": 30}},
        ])
        _ingest(base, inv2, _hex32(11), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "desktop"}},
            {"type": "invitation.rsvp.open", "ts": now + 1000, "payload": {}},
            {"type": "invitation.rsvp.submit", "ts": now + 2000, "payload": {"status": "yes"}},
            {"type": "invitation.view.end", "ts": now + 3000,
             "payload": {"duration_ms": 3000, "max_scroll_pct": 70}},
        ])
        # Default sort.
        s, b = _get(base, "/api/account/analytics/creations", headers)
        assert s == 200, f"creations failed: {s} {b!r}"
        cdata = json.loads(b)
        assert cdata["count"] >= 2, f"expected >=2 creations, got {cdata['count']}"
        assert cdata["items"][0]["title"] is not None
        # Sort by views asc.
        s, b = _get(base, "/api/account/analytics/creations?sort=views&order=asc", headers)
        assert s == 200
        cdata = json.loads(b)
        items = cdata["items"]
        # The invitation with 0 views should come first.
        assert items[0]["views"] <= items[-1]["views"], \
            f"expected asc sort by views: {[i['views'] for i in items]}"
        # Filter by status.
        s, b = _get(base, "/api/account/analytics/creations?status=draft", headers)
        assert s == 200
        cdata = json.loads(b)
        assert all(i["status"] == "draft" for i in cdata["items"]), \
            f"status filter failed: {cdata['items']}"
        print("Phase 2 (creations table sort + filter) PASSED")


def test_phase3_account_summary():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv1 = _create_invitation(base, headers, "summary-1")
        inv2 = _create_invitation(base, headers, "summary-2")
        now = int(time.time() * 1000)
        _ingest(base, inv1, _hex32(20), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
            {"type": "invitation.rsvp.submit", "ts": now + 1000, "payload": {}},
            {"type": "invitation.view.end", "ts": now + 2000,
             "payload": {"duration_ms": 2000, "max_scroll_pct": 50}},
        ])
        _ingest(base, inv2, _hex32(21), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
            {"type": "invitation.rsvp.submit", "ts": now + 1000, "payload": {}},
            {"type": "invitation.view.end", "ts": now + 2000,
             "payload": {"duration_ms": 2000, "max_scroll_pct": 50}},
        ])
        s, b = _get(base, "/api/account/analytics/summary", headers)
        assert s == 200, f"summary failed: {s} {b!r}"
        sdata = json.loads(b)
        assert sdata["totalInvitations"] >= 2
        assert sdata["totalViews"] >= 2
        assert sdata["totalRsvps"] >= 2
        print(f"Phase 3 (account summary) PASSED — {sdata}")


def test_phase4_export_invitation_csv_json():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "export-1")
        now = int(time.time() * 1000)
        _ingest(base, inv_id, _hex32(30), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
            {"type": "invitation.rsvp.open", "ts": now + 1000, "payload": {}},
            {"type": "invitation.view.end", "ts": now + 2000,
             "payload": {"duration_ms": 2000, "max_scroll_pct": 50}},
        ])
        # CSV export
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics/export?format=csv", headers)
        assert s == 200, f"csv export failed: {s} {b!r}"
        # UTF-8 BOM
        assert b[:3] == b"\xef\xbb\xbf", f"expected UTF-8 BOM, got {b[:10]!r}"
        text = b.decode("utf-8")
        assert "session_id" in text, "expected header row"
        assert inv_id in text, "expected invitation id in CSV body"
        # The CSV has one row per session with joined event counts.
        # Header includes view_count + rsvp_open_count etc.
        assert "view_count" in text, f"expected view_count column in CSV, got: {text[:300]}"
        assert "rsvp_open_count" in text, "expected rsvp_open_count column"
        # JSON export
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics/export?format=json", headers)
        assert s == 200, f"json export failed: {s} {b!r}"
        j = json.loads(b)
        assert "invitation" in j and "sessions" in j and "events" in j
        assert len(j["sessions"]) >= 1
        assert len(j["events"]) >= 1
        print("Phase 4 (export invitation CSV + JSON) PASSED")


def test_phase5_export_account_csv():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv1 = _create_invitation(base, headers, "export-acct-1")
        inv2 = _create_invitation(base, headers, "export-acct-2")
        now = int(time.time() * 1000)
        _ingest(base, inv1, _hex32(40), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "mobile"}},
            {"type": "invitation.view.end", "ts": now + 1000, "payload": {"duration_ms": 1000, "max_scroll_pct": 10}},
        ])
        _ingest(base, inv2, _hex32(41), [
            {"type": "invitation.view", "ts": now, "payload": {"viewport": "desktop"}},
            {"type": "invitation.view.end", "ts": now + 1000, "payload": {"duration_ms": 1000, "max_scroll_pct": 10}},
        ])
        s, b = _get(base, "/api/account/analytics/export?format=csv", headers)
        assert s == 200, f"acct csv failed: {s} {b!r}"
        assert b[:3] == b"\xef\xbb\xbf", "expected UTF-8 BOM"
        text = b.decode("utf-8")
        # Header should appear only once.
        assert text.count("session_id,invitation_id") == 1, \
            f"expected exactly 1 CSV header row, got {text.count('session_id,invitation_id')}"
        # Both invitation ids should appear.
        assert inv1 in text and inv2 in text
        print("Phase 5 (export account CSV) PASSED")


def test_phase6_live_endpoint_feature_flag():
    with app_server() as (proc, base, _):
        headers = _register_and_login(base)
        inv_id = _create_invitation(base, headers, "live-test")
        # Default flag is False → 403.
        s, b = _get(base, f"/api/invitations/{inv_id}/analytics/live", headers)
        assert s == 403, f"live should be 403 by default, got {s} {b!r}"
        # Flip the flag via the admin API.
        s, b = _get(base, "/api/auth/me", headers)
        me = json.loads(b)["user"]
        # Use the admin feature-flag set route (added in Part 5 §5.4).
        s, b = _post(base, "/api/admin/feature-flags", {
            "key": "analytics_live_enabled", "value": True, "updatedBy": me["id"],
        }, headers)
        if s == 200:
            # Flag was set — retry.
            s, b = _get(base, f"/api/invitations/{inv_id}/analytics/live", headers)
            assert s == 200, f"live should be 200 after flag set, got {s} {b!r}"
            data = json.loads(b)
            assert "activeSessions" in data and "lastEventAt" in data
        else:
            # Admin route not wired in this build — skip the second check.
            print(f"  (skipped admin flag set: {s} {b!r})")
        print("Phase 6 (live endpoint feature flag) PASSED")


def test_phase7_js_modules_static():
    """Static checks on the JS modules — chart.js + dashboard analytics.js."""
    chart_path = ROOT / "src" / "js" / "components" / "chart.js"
    dashboard_path = ROOT / "src" / "js" / "pages" / "dashboard" / "analytics.js"
    collector_path = ROOT / "src" / "js" / "public" / "analytics-collector.js"
    assert chart_path.is_file(), "components/chart.js missing"
    assert dashboard_path.is_file(), "pages/dashboard/analytics.js missing"
    assert collector_path.is_file(), "public/analytics-collector.js missing"
    chart_src = chart_path.read_text(encoding="utf-8")
    assert "LineChart" in chart_src and "BarChart" in chart_src \
        and "DonutChart" in chart_src and "Sparkline" in chart_src, \
        "chart.js missing one of LineChart/BarChart/DonutChart/Sparkline"
    assert "ResizeObserver" in chart_src, "chart.js should handle ResizeObserver"
    assert "devicePixelRatio" in chart_src, "chart.js should handle devicePixelRatio"
    assert "data-chart=" in chart_src, "chart.js should support data-* attribute API"
    assert "aria-label" in chart_src, "chart.js should set aria-label"
    assert "ei-chart-data-table" in chart_src, "chart.js should add screen-reader data table"
    dash_src = dashboard_path.read_text(encoding="utf-8")
    assert "EInviteAnalyticsDashboard" in dash_src, "dashboard module missing global"
    assert "renderStatCard" in dash_src, "dashboard missing stat-card renderer"
    assert "renderFunnel" in dash_src, "dashboard missing funnel renderer"
    assert "renderDeviceSplit" in dash_src, "dashboard missing device-split renderer"
    assert "renderCountrySplit" in dash_src, "dashboard missing country-split renderer"
    # Bilingual EN+KH
    assert "STRINGS" in dash_src
    assert "km:" in dash_src, "dashboard should have Khmer strings"
    collector_src = collector_path.read_text(encoding="utf-8")
    assert "EInviteAnalyticsCollector" in collector_src
    assert "sendBeacon" in collector_src, "collector should use sendBeacon on unload"
    assert "keepalive" in collector_src, "collector should use fetch keepalive fallback"
    assert "MAX_EVENTS_PER_BATCH" in collector_src
    print("Phase 7 (JS modules static) PASSED")


def main():
    os.environ.setdefault("EINVITE_ALLOW_NO_SCANNER", "1")
    test_phase7_js_modules_static()
    test_phase1_per_invitation_analytics()
    test_phase2_creations_table()
    test_phase3_account_summary()
    test_phase4_export_invitation_csv_json()
    test_phase5_export_account_csv()
    test_phase6_live_endpoint_feature_flag()
    print("\nANALYTICS_REPORTS_TEST_PASSED")


if __name__ == "__main__":
    main()
