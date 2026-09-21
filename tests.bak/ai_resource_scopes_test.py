#!/usr/bin/env python3
"""V54.15 (sec-6 — §2.6) — Resource-scoped permissions Stage 3.

Real-HTTP integration test (mirrors the pattern in
``tests/ai_jit_enforcement_test.py``) that spins up an in-process
``ThreadingHTTPServer`` and exercises the new resource-scoped grant
lifecycle end-to-end:

Coverage matrix:
  - **Grant allows non-owner** — host B (a ``viewer`` collaborator on
    event1) is granted ``event:event1:publish``.  ``publish.prepare``
    appears in B's available tools list for event1 because the new
    grant check is authoritative (legacy tier check denies — viewer not
    in {owner, manager}).  A ``shadow_eval_divergence`` log entry is
    emitted (new_check=allow, legacy_check=deny).
  - **No grant for different event** — the same B calls the tools
    endpoint against event2 (also owned by A).  ``publish.prepare`` is
    NOT in the available list (no grant matches event2; legacy also
    denies).  No divergence (both deny).
  - **Owner + no grant → legacy authoritative** — host A (the owner)
    calls the tools endpoint against event1.  ``publish.prepare`` is in
    the available list (legacy tier check allows — owner).  A
    ``no_grant_legacy_authoritative`` log entry is emitted (A has no
    grants of any kind).
  - **Revoke** — after host A revokes the grant, B's call against
    event1 no longer lists ``publish.prepare`` (no grant + legacy deny
    → deny).
  - **Audit events** — ``grant.created`` and ``grant.revoked`` are
    written to the hash-chained ``audit_events`` table.
  - **Route security** — a non-host (an outsider with no access to
    event1) cannot create a grant for event1 (``403 grant_not_host``)
    and cannot revoke an existing grant they did not create
    (``403 grant_not_authorised_to_revoke``).

Acceptance: prints ``AI_RESOURCE_SCOPES_TEST_PASSED`` on success.
"""
from __future__ import annotations
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('EINVITE_DEV_AUTH_TOKENS', '1')
os.environ.setdefault('EINVITE_REQUIRE_VERIFIED_EMAIL', '0')
os.environ.setdefault('EINVITE_ALLOW_NO_SCANNER', '1')
os.environ.setdefault('EINVITE_PRODUCTION', '0')
os.environ.setdefault('EINVITE_AI_FAKE_PROVIDER', '1')
os.environ.setdefault('EINVITE_AI_PROVIDER', 'fake')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src' / 'python'))


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def http_json(base, path, method='GET', body=None, token=None, expected=200):
    data = None if body is None else json.dumps(body).encode('utf-8')
    headers = {'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    payload = json.loads(raw or b'{}')
    if expected is not None:
        assert status == expected, (
            f'{method} {path}: expected {expected}, got {status}: {payload}'
        )
    return status, payload


def lookup_user_id(server, email):
    with server.connect() as db:
        row = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        return row['id'] if row else None


def lookup_invitation_id(server, slug):
    with server.connect() as db:
        row = db.execute("SELECT id FROM invitations WHERE slug=?", (slug,)).fetchone()
        return row['id'] if row else None


def fetch_audit_actions(server, user_id, prefix='grant.'):
    with server.connect() as db:
        return [
            r['action']
            for r in db.execute(
                "SELECT action FROM audit_events WHERE user_id=? AND action LIKE ? ORDER BY created_at",
                (user_id, prefix + '%'),
            ).fetchall()
        ]


def list_available_tool_ids(base, invitation_id, token):
    """GET /api/ai-agent/tools?invitationId=... — returns the capability_catalog
    payload (``{version, tools:[...], denied:[...], access, coverage}``).
    """
    _, payload = http_json(
        base, f'/api/ai-agent/tools?invitationId={invitation_id}',
        token=token, expected=200,
    )
    return [t['id'] for t in payload.get('tools', [])], payload


def run():
    with tempfile.TemporaryDirectory(prefix='einvite-sec6-scopes-') as data_dir:
        os.environ['EINVITE_DATA_DIR'] = data_dir
        import server  # noqa: E402  (import after env is set)
        from ai_agent import capabilities as caps

        port = free_port()
        httpd = server.ThreadingHTTPServer(('127.0.0.1', port), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{port}'
        try:
            # ─── Setup: register host A + host B ──────────────────────────
            password = 'StrongPassw0rd!'
            email_a = 'sec6-host-a@example.com'
            email_b = 'sec6-host-b@example.com'
            http_json(base, '/api/auth/register', 'POST',
                      {'email': email_a, 'password': password}, expected=201)
            http_json(base, '/api/auth/register', 'POST',
                      {'email': email_b, 'password': password}, expected=201)
            _, auth_a = http_json(base, '/api/auth/login', 'POST',
                                  {'email': email_a, 'password': password}, expected=201)
            _, auth_b = http_json(base, '/api/auth/login', 'POST',
                                  {'email': email_b, 'password': password}, expected=201)
            token_a = auth_a['token']
            token_b = auth_b['token']
            host_a_id = lookup_user_id(server, email_a)
            host_b_id = lookup_user_id(server, email_b)
            assert host_a_id and host_b_id, (host_a_id, host_b_id)

            # ─── Setup: A creates event1 + event2 ─────────────────────────
            document = {
                'schemaVersion': 14,
                'eventType': 'Wedding',
                'fields': {'names': 'Sec6 Couple'},
                'objects': {
                    'title': {'type': 'text', 'text': 'Sec6 Couple', 'left': '10%', 'top': '10%',
                              'width': '80%', 'height': '80px', 'zIndex': 1},
                },
                'designPages': [],
                'settings': {'rsvpEnabled': True},
            }
            _, created1 = http_json(base, '/api/invitations', 'POST',
                                    {'slug': 'sec6-event1', 'document': document},
                                    token_a, 201)
            _, created2 = http_json(base, '/api/invitations', 'POST',
                                    {'slug': 'sec6-event2', 'document': document},
                                    token_a, 201)
            event1_id = created1['id']
            event2_id = created2['id']
            assert event1_id and event2_id

            # ─── Setup: A adds B as a viewer collaborator on BOTH events ──
            # ``viewer`` role means:
            #   - can_read_invitation(B, event_i) → True  (so /api/ai-agent/tools works)
            #   - legacy tier check on publish.prepare (permission=manage) → DENY
            #     (viewer not in {owner, manager})
            # So the legacy path denies publish.prepare for B; only a
            # resource-scoped grant can flip it to allow.
            http_json(base, f'/api/invitations/{event1_id}/collaborators', 'POST',
                      {'email': email_b, 'role': 'viewer'}, token_a, 200)
            http_json(base, f'/api/invitations/{event2_id}/collaborators', 'POST',
                      {'email': email_b, 'role': 'viewer'}, token_a, 200)

            # ─── Scenario 0: BEFORE grant — B cannot publish event1 ────────
            caps.reset_shadow_eval_logs()
            tools_b0, _ = list_available_tool_ids(base, event1_id, token_b)
            assert 'publish.prepare' not in tools_b0, (
                'B (viewer) must NOT have publish.prepare before any grant is issued'
            )

            # ─── Scenario 1: A grants B `event:event1:publish` ────────────
            _, grant_resp = http_json(
                base, '/api/account/grants', 'POST',
                {
                    'user_id': host_b_id,
                    'resource_type': 'event',
                    'resource_id': event1_id,
                    'action': 'publish',
                    'reason': 'sec-6 test grant: allow B to publish event1',
                },
                token_a, 201,
            )
            assert grant_resp.get('grantId'), grant_resp
            grant_id = grant_resp['grantId']
            assert grant_resp['resourceType'] == 'event'
            assert grant_resp['resourceId'] == event1_id
            assert grant_resp['action'] == 'publish'

            # Audit: grant.created is in audit_events for user_id=host_a_id.
            actions_a = fetch_audit_actions(server, host_a_id)
            assert 'grant.created' in actions_a, actions_a

            # ─── Scenario 2: B's call to publish.prepare on event1 succeeds
            # (new grant check authoritative — legacy denies for viewer).
            caps.reset_shadow_eval_logs()
            tools_b1, _ = list_available_tool_ids(base, event1_id, token_b)
            assert 'publish.prepare' in tools_b1, (
                'B must have publish.prepare on event1 after the grant (new check authoritative)'
            )
            logs_b1 = caps.recent_shadow_eval_logs(limit=200)
            divergences = [
                l for l in logs_b1
                if l.get('event') == 'shadow_eval_divergence'
                and l.get('tool_id') == 'publish.prepare'
                and l.get('new_check') == 'allow'
                and l.get('legacy_check') == 'deny'
                and l.get('user_id') == host_b_id
                and l.get('resource') == f'event:{event1_id}:publish'
            ]
            assert divergences, (
                f'shadow_eval_divergence (new=allow, legacy=deny) must be logged for '
                f'B on event1; got logs: {logs_b1}'
            )

            # ─── Scenario 3: B's call to publish.prepare on event2 fails ─
            # (B has a grant only for event1, not event2; legacy also denies
            # for viewer — both deny → no divergence).
            caps.reset_shadow_eval_logs()
            tools_b2, _ = list_available_tool_ids(base, event2_id, token_b)
            assert 'publish.prepare' not in tools_b2, (
                'B must NOT have publish.prepare on event2 (no grant for event2; legacy denies)'
            )
            logs_b2 = caps.recent_shadow_eval_logs(limit=200)
            # For publish.prepare specifically: B has a grant for
            # event/publish (the event1 one), so the new check is
            # authoritative even when the resource_id differs.  This
            # means NO no_grant log should fire for publish.prepare on
            # event2 — the new check ran (and denied, because event1 !=
            # event2), it did not fall back to legacy.
            publish_logs_b2 = [l for l in logs_b2 if l.get('tool_id') == 'publish.prepare']
            assert all(
                l.get('event') != 'no_grant_legacy_authoritative' for l in publish_logs_b2
            ), (
                f'B has a grant for event/publish (event1) so the new check is '
                f'authoritative for publish.prepare even on event2 — no no_grant log '
                f'should fire for publish.prepare: {publish_logs_b2}'
            )

            # ─── Scenario 4: A's call to publish.prepare on event1 succeeds
            # (legacy tier check allows — owner; A has NO grant of any kind
            # → legacy is authoritative → no_grant_legacy_authoritative log).
            caps.reset_shadow_eval_logs()
            tools_a1, _ = list_available_tool_ids(base, event1_id, token_a)
            assert 'publish.prepare' in tools_a1, (
                'A (owner) must have publish.prepare on event1 (legacy tier check)'
            )
            logs_a1 = caps.recent_shadow_eval_logs(limit=200)
            no_grant_logs = [
                l for l in logs_a1
                if l.get('event') == 'no_grant_legacy_authoritative'
                and l.get('tool_id') == 'publish.prepare'
                and l.get('user_id') == host_a_id
                and l.get('legacy_check') == 'allow'
            ]
            assert no_grant_logs, (
                f'no_grant_legacy_authoritative must be logged for A (owner, no grant) '
                f'on event1; got logs: {logs_a1}'
            )

            # ─── Scenario 5: Revoke the grant ─────────────────────────────
            _, revoke_resp = http_json(
                base, f'/api/account/grants/{grant_id}?reason=test-revocation',
                'DELETE', token=token_a, expected=200,
            )
            assert revoke_resp.get('ok') is True, revoke_resp
            # Audit: grant.revoked is in audit_events for user_id=host_a_id.
            actions_a_after = fetch_audit_actions(server, host_a_id)
            assert 'grant.revoked' in actions_a_after, actions_a_after

            # ─── Scenario 6: B's call to publish.prepare on event1 now fails
            # (no active grant → legacy tier check authoritative → deny for viewer).
            caps.reset_shadow_eval_logs()
            tools_b3, _ = list_available_tool_ids(base, event1_id, token_b)
            assert 'publish.prepare' not in tools_b3, (
                'B must NOT have publish.prepare on event1 after revocation'
            )
            logs_b3 = caps.recent_shadow_eval_logs(limit=200)
            no_grant_logs_b3 = [
                l for l in logs_b3
                if l.get('event') == 'no_grant_legacy_authoritative'
                and l.get('tool_id') == 'publish.prepare'
                and l.get('user_id') == host_b_id
                and l.get('legacy_check') == 'deny'
            ]
            assert no_grant_logs_b3, (
                f'after revocation, B has no grant for event/publish → no_grant log '
                f'must fire with legacy_check=deny: {logs_b3}'
            )

            # ─── Scenario 7: GET /api/account/grants lists the (revoked) grant
            _, grants_list = http_json(
                base, '/api/account/grants', token=token_b, expected=200,
            )
            assert any(g['id'] == grant_id for g in grants_list['grants']), grants_list
            revoked_entry = next(g for g in grants_list['grants'] if g['id'] == grant_id)
            assert revoked_entry['revokedAt'] is not None, revoked_entry
            assert revoked_entry['action'] == 'publish'
            assert revoked_entry['resourceType'] == 'event'
            assert revoked_entry['resourceId'] == event1_id

            # ─── Scenario 8: Route security — outsider cannot create / revoke
            email_outsider = 'sec6-outsider@example.com'
            http_json(base, '/api/auth/register', 'POST',
                      {'email': email_outsider, 'password': password}, expected=201)
            _, auth_o = http_json(base, '/api/auth/login', 'POST',
                                  {'email': email_outsider, 'password': password}, expected=201)
            token_o = auth_o['token']
            # Outsider attempts to grant themselves publish on event1 → 403.
            status, err_o = http_json(
                base, '/api/account/grants', 'POST',
                {
                    'user_id': lookup_user_id(server, email_outsider),
                    'resource_type': 'event',
                    'resource_id': event1_id,
                    'action': 'publish',
                },
                token_o, expected=None,
            )
            assert status == 403, f'outsider grant must be 403; got {status}: {err_o}'
            assert err_o.get('code') == 'grant_not_host', err_o

            # A creates a fresh grant for B so we can test outsider revoke.
            _, grant_resp2 = http_json(
                base, '/api/account/grants', 'POST',
                {
                    'user_id': host_b_id,
                    'resource_type': 'event',
                    'resource_id': event1_id,
                    'action': 'publish',
                },
                token_a, 201,
            )
            grant_id2 = grant_resp2['grantId']
            # Outsider attempts to revoke → 403.
            status, err_o2 = http_json(
                base, f'/api/account/grants/{grant_id2}', 'DELETE',
                token=token_o, expected=None,
            )
            assert status == 403, f'outsider revoke must be 403; got {status}: {err_o2}'
            assert err_o2.get('code') == 'grant_not_authorised_to_revoke', err_o2
            # The grant is still active.
            with server.connect() as db:
                row = db.execute(
                    "SELECT revoked_at FROM agent_grants WHERE id=?", (grant_id2,),
                ).fetchone()
            assert row['revoked_at'] is None, 'outsider must not have revoked the grant'

            # ─── Scenario 9: Grant grammar validation ────────────────────
            # POST with a malformed action (uppercase letters) → 400.
            status, err_grammar = http_json(
                base, '/api/account/grants', 'POST',
                {
                    'user_id': host_b_id,
                    'resource_type': 'event',
                    'resource_id': event1_id,
                    'action': 'PUBLISH',  # uppercase — rejected by Grant grammar
                },
                token_a, expected=None,
            )
            assert status == 400, f'malformed action must be 400; got {status}: {err_grammar}'
            assert err_grammar.get('code') == 'grant_invalid_syntax', err_grammar

        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)

    print('AI_RESOURCE_SCOPES_TEST_PASSED')
    return 0


def test_ai_resource_scopes():
    """Pytest-compatible entry point."""
    rc = run()
    assert rc == 0


if __name__ == '__main__':
    sys.exit(run())
