#!/usr/bin/env python3
"""V54.13 (sec-5 — §2.5) — Enforce JIT elevation.

Real-HTTP integration test that runs an in-process ``ThreadingHTTPServer`` so
the test process can also reach into the SQLite DB directly (via
``server.connect``) to construct plans, expire grants, and inspect audit
events.

The Phase 1a skeleton (``ai_agent/jit_elevation.py::evaluate()``) returned
``True`` unconditionally — anyone reading V54.6 would have assumed JIT
elevation was live when in fact nothing was enforced. This test closes that
gap by exercising the full JIT lifecycle through the existing
``/api/invitations/{iid}/ai/plans/{plan_id}/authorize`` endpoint:

Coverage matrix:
  - **Manual approval** — an owner calling ``message.prepare_send`` (a
    JIT-eligible tool that is NOT in the auto-approval set) receives
    ``{needsElevation: true, requestId: ...}`` instead of an authorization
    token. After the host approves via ``POST /api/ai-agent/jit/approve``,
    the same authorize call succeeds with ``{authorized: true}``.
  - **Expiry** — after the 5-minute TTL elapses (simulated by setting
    ``expires_at`` to a past timestamp in the DB), the same authorize call
    returns ``needsElevation`` again (the consumed grant is now expired).
  - **Read/edit skip JIT** — ``object.update`` (permission=edit, NOT in
    JIT_ELIGIBLE_TOOLS) succeeds immediately without any elevation request.
  - **Auto-approval** — an owner calling ``publish.prepare`` (auto-approved
    per §4.1 because the requester is owner/manager AND the tool is in
    AUTO_APPROVED_TOOLS) succeeds immediately without manual approval.
  - **Deny** — ``POST /api/ai-agent/jit/deny`` transitions the elevation to
    ``status='denied'`` and the next authorize call creates a NEW request
    (the denied one cannot be re-used).
  - **Audit events** — ``jit.requested``, ``jit.granted``, ``jit.consumed``,
    ``jit.denied``, ``jit.expired`` are all emitted to the hash-chained
    ``audit_events`` table.
  - **Negative proof** — monkey-patching ``JITElevationManager.evaluate`` to
    return ``True`` (the old Phase 1a stub) makes the manual-approval
    scenario succeed without elevation. This proves the wiring is
    load-bearing — if JIT enforcement were disabled, the test scenarios
    above would fail.

Acceptance: prints ``AI_JIT_ENFORCEMENT_TEST_PASSED`` on success.
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
from unittest import mock

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


def fetch_audit_actions(server, user_id):
    with server.connect() as db:
        return [
            r['action']
            for r in db.execute(
                "SELECT action FROM audit_events WHERE user_id=? AND action LIKE 'jit.%' ORDER BY created_at",
                (user_id,),
            ).fetchall()
        ]


def make_plan_dict(tool_calls, summary='JIT test plan'):
    """Build a plan dict shaped like AgentService.stream_message() would."""
    high_risk = any(call.get('risk') == 'high' for call in tool_calls)
    confirmations = any(call.get('confirmationRequired') for call in tool_calls)
    return {
        'summary': summary,
        'toolCalls': tool_calls,
        'affectedPages': sorted({str(c['arguments'].get('pageId')) for c in tool_calls if c['arguments'].get('pageId')}),
        'affectedObjectIds': sorted({str(v) for c in tool_calls for v in (c['arguments'].get('objectIds') or c['arguments'].get('recipientIds') or [])}),
        'estimatedActionCount': len(tool_calls),
        'confirmationRequired': bool(confirmations or high_risk),
        'confirmationReasons': [c['reason'] or c['id'] for c in tool_calls if c.get('confirmationRequired') or c.get('risk') == 'high'],
        'autoApplyEligible': False,
        'providerMode': 'fake',
    }


def make_tool_call(server_module, tool_id, arguments, reason='Test tool call'):
    """Validate a tool call via the existing validate_tool_call helper."""
    from ai_agent.tools import validate_tool_call
    return validate_tool_call({'id': tool_id, 'arguments': arguments, 'reason': reason})


def create_confirmed_plan(service, invitation_id, user_id, role, tool_calls, idem_key):
    """Create + confirm a plan via the AgentService store layer (bypasses the LLM)."""
    conversation = service.store.create_conversation(invitation_id, user_id, 'JIT test', 'fake')
    conversation_id = conversation['id']
    # Read the current invitation revision + fingerprint (confirm_plan checks both).
    # revision = updated_at (per ai_agent/context.py L121); fingerprint is
    # computed from the draft_json via ai_agent.context.fingerprint(document).
    from ai_agent.context import fingerprint as compute_fingerprint
    with service.connect() as db:
        row = db.execute(
            "SELECT draft_json, updated_at FROM invitations WHERE id=?",
            (invitation_id,),
        ).fetchone()
        revision = int(row['updated_at'] if row and row['updated_at'] is not None else 0)
        try:
            document = json.loads(row['draft_json'] or '{}')
        except Exception:
            document = {}
        fingerprint = compute_fingerprint(document)
    plan_value = make_plan_dict(tool_calls, summary=f'JIT plan {idem_key}')
    plan = service.store.create_plan(
        conversation_id, invitation_id, user_id,
        revision, fingerprint, plan_value, idempotency_key=idem_key,
    )
    plan_id = plan['id']
    service.confirm_plan(
        invitation_id, user_id, role, plan_id,
        {'exactTargetsAccepted': True, 'destructiveAccepted': True, 'context': {}},
    )
    return plan_id


def run():
    with tempfile.TemporaryDirectory(prefix='einvite-sec5-jit-') as data_dir:
        os.environ['EINVITE_DATA_DIR'] = data_dir
        import server  # noqa: E402  (import after env is set)

        port = free_port()
        httpd = server.ThreadingHTTPServer(('127.0.0.1', port), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{port}'
        try:
            service = server.get_ai_agent_service()
            # ─── Setup: register host + invitation ─────────────────────────
            email_host = 'sec5-jit-host@example.com'
            password = 'StrongPassw0rd!'
            _, auth = http_json(base, '/api/auth/register', 'POST',
                               {'email': email_host, 'password': password}, expected=201)
            token_host = auth['token']
            host_id = lookup_user_id(server, email_host)
            assert host_id, 'host registration failed'

            document = {
                'schemaVersion': 14,
                'eventType': 'Wedding',
                'fields': {'names': 'JIT Couple'},
                'objects': {
                    'title': {'type': 'text', 'text': 'JIT Couple', 'left': '10%', 'top': '10%', 'width': '80%', 'height': '80px', 'zIndex': 1},
                },
                'designPages': [],
                'settings': {'rsvpEnabled': True},
            }
            _, created = http_json(base, '/api/invitations', 'POST',
                                  {'slug': 'sec5-jit-invitation', 'document': document},
                                  token_host, 201)
            invite_id = created['id']
            assert invite_id, 'invitation creation failed'

            # ─── Scenario 1: Manual approval flow ──────────────────────────
            # message.prepare_send is JIT-eligible (high risk, in JIT_ELIGIBLE_TOOLS)
            # but NOT in AUTO_APPROVED_TOOLS — even an owner must get manual
            # approval. The authorize endpoint must return needsElevation.
            msg_call = make_tool_call(
                server, 'message.prepare_send',
                {'channel': 'email', 'recipientIds': ['guest-1'], 'message': 'You are invited!'},
                reason='Send the wedding announcement email',
            )
            plan_id_msg = create_confirmed_plan(
                service, invite_id, host_id, 'owner', [msg_call], 'sec5-jit-msg-plan',
            )

            status, resp = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp.get('needsElevation') is True, (
                f'message.prepare_send must require elevation; got: {resp}'
            )
            assert resp.get('toolId') == 'message.prepare_send', resp
            assert resp.get('ttlSeconds') == 300, resp
            assert resp.get('requestId'), f'requestId missing from needsElevation response: {resp}'
            request_id_1 = resp['requestId']
            assert resp.get('status') == 'requested', resp
            assert resp.get('autoEligible') is False, resp
            # The response must NOT contain an authorization token.
            assert 'authorizationToken' not in resp, (
                f'needsElevation response must not include authorizationToken: {resp}'
            )

            # The jit_elevations row should now exist in 'requested' status.
            elev = service.jit.get_elevation(request_id_1)
            assert elev is not None, 'elevation row not created'
            assert elev['status'] == 'requested', elev
            assert elev['toolId'] == 'message.prepare_send', elev
            assert elev['userId'] == host_id, elev
            assert elev['invitationId'] == invite_id, elev

            # GET /api/ai-agent/jit/pending lists the pending request for the host.
            status, pending = http_json(
                base, f'/api/ai-agent/jit/pending?invitationId={invite_id}',
                token=token_host, expected=200,
            )
            pending_ids = [r['id'] for r in pending['requests']]
            assert request_id_1 in pending_ids, (
                f'pending list must include the just-created request: {pending}'
            )

            # Approve the request via POST /api/ai-agent/jit/approve.
            status, approved = http_json(
                base, '/api/ai-agent/jit/approve', 'POST',
                {'request_id': request_id_1}, token_host, expected=200,
            )
            assert approved.get('ok') is True, approved
            assert approved.get('expires_at'), approved
            # The elevation row should now be 'granted'.
            elev_after = service.jit.get_elevation(request_id_1)
            assert elev_after['status'] == 'granted', elev_after
            assert elev_after['expiresAt'] is not None, elev_after

            # Re-call authorize → now it should succeed (the grant is consumed).
            status, resp2 = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp2.get('authorized') is True, (
                f'authorize must succeed after approval; got: {resp2}'
            )
            assert resp2.get('toolId') == 'message.prepare_send', resp2
            assert resp2.get('authorizationToken'), resp2
            assert resp2.get('expiresInSeconds') == 30, resp2
            # The grant is now consumed (consumed_at IS NOT NULL).
            elev_consumed = service.jit.get_elevation(request_id_1)
            assert elev_consumed['consumedAt'] is not None, (
                f'grant must be marked consumed after authorize: {elev_consumed}'
            )

            # ─── Scenario 2: Expiry ─────────────────────────────────────────
            # Force the grant's expires_at into the past. The next authorize
            # call should sweep_expired() it to status='expired' and surface
            # needsElevation again (the consumed grant is dead; a NEW request
            # is created for the next attempt).
            with server.connect() as db:
                db.execute(
                    "UPDATE jit_elevations SET expires_at=? WHERE id=?",
                    (int(time.time() * 1000) - 1000, request_id_1),
                )
            status, resp3 = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp3.get('needsElevation') is True, (
                f'expired grant must trigger needsElevation again; got: {resp3}'
            )
            assert resp3.get('requestId') != request_id_1, (
                'expired grant must result in a NEW elevation request, not the old one',
                resp3,
            )
            # The old grant is now expired (sweep_expired transitioned it).
            elev_old = service.jit.get_elevation(request_id_1)
            assert elev_old['status'] == 'expired', (
                f'old grant must be status=expired after sweep; got: {elev_old}'
            )

            # ─── Scenario 3: Read/edit tools DON'T require elevation ───────
            # object.update has permission="edit" and is NOT in JIT_ELIGIBLE_TOOLS.
            # The authorize endpoint must succeed immediately without any
            # needsElevation response.
            edit_call = make_tool_call(
                server, 'object.update',
                {'pageId': 'hero', 'objectIds': ['title'], 'patch': {'text': 'Updated text'}},
                reason='Update the title text',
            )
            plan_id_edit = create_confirmed_plan(
                service, invite_id, host_id, 'owner', [edit_call], 'sec5-jit-edit-plan',
            )
            status, resp_edit = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_edit}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp_edit.get('authorized') is True, (
                f'object.update must not require JIT elevation; got: {resp_edit}'
            )
            assert resp_edit.get('toolId') == 'object.update', resp_edit
            assert 'needsElevation' not in resp_edit, (
                f'edit tools must never return needsElevation: {resp_edit}'
            )
            # No new jit_elevations row should have been created for object.update.
            with server.connect() as db:
                row = db.execute(
                    "SELECT COUNT(*) c FROM jit_elevations WHERE tool_id=? AND user_id=?",
                    ('object.update', host_id),
                ).fetchone()
                assert int(row['c']) == 0, (
                    f'no jit_elevations row should exist for object.update: count={row["c"]}'
                )

            # ─── Scenario 4: Auto-approval (publish.prepare + owner) ────────
            # publish.prepare is JIT-eligible AND in AUTO_APPROVED_TOOLS for
            # owners/managers. The authorize call must succeed immediately
            # WITHOUT a manual approval step (no needsElevation response).
            publish_call = make_tool_call(
                server, 'publish.prepare',
                {'action': 'publish'},
                reason='Publish the wedding invitation',
            )
            plan_id_pub = create_confirmed_plan(
                service, invite_id, host_id, 'owner', [publish_call], 'sec5-jit-publish-plan',
            )
            status, resp_pub = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_pub}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp_pub.get('authorized') is True, (
                f'publish.prepare must auto-approve for owner; got: {resp_pub}'
            )
            assert resp_pub.get('toolId') == 'publish.prepare', resp_pub
            assert 'needsElevation' not in resp_pub, (
                f'auto-approved publish.prepare must NOT return needsElevation: {resp_pub}'
            )
            # An auto-approved elevation row exists for publish.prepare with
            # status='granted' and auto_eligible=1 (now consumed).
            with server.connect() as db:
                row = db.execute(
                    "SELECT status, auto_eligible, consumed_at FROM jit_elevations "
                    "WHERE tool_id=? AND user_id=? ORDER BY created_at DESC LIMIT 1",
                    ('publish.prepare', host_id),
                ).fetchone()
                assert row is not None, 'auto-approved publish.prepare must create a jit_elevations row'
                assert row['status'] == 'granted', row
                assert int(row['auto_eligible']) == 1, (
                    f'auto-approved grant must have auto_eligible=1; got: {row}'
                )
                assert row['consumed_at'] is not None, (
                    'auto-approved grant must be consumed by authorize_tool_call'
                )

            # ─── Scenario 5: Deny flow ──────────────────────────────────────
            # Create a new message.prepare_send plan + authorize → needsElevation.
            # Deny the request via POST /api/ai-agent/jit/deny. The next
            # authorize call must create a NEW request (the denied one cannot
            # be reused).
            msg_call_2 = make_tool_call(
                server, 'message.prepare_send',
                {'channel': 'sms', 'recipientIds': ['guest-2'], 'message': 'SMS reminder'},
                reason='Send an SMS reminder',
            )
            plan_id_msg2 = create_confirmed_plan(
                service, invite_id, host_id, 'owner', [msg_call_2], 'sec5-jit-msg2-plan',
            )
            status, resp_msg2 = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg2}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp_msg2.get('needsElevation') is True, resp_msg2
            request_id_2 = resp_msg2['requestId']

            status, denied = http_json(
                base, '/api/ai-agent/jit/deny', 'POST',
                {'request_id': request_id_2, 'reason': 'Not allowed at this time'},
                token_host, expected=200,
            )
            assert denied.get('ok') is True, denied
            # The elevation row is now 'denied'.
            elev_denied = service.jit.get_elevation(request_id_2)
            assert elev_denied['status'] == 'denied', elev_denied
            assert elev_denied['revokedAt'] is not None, elev_denied

            # Next authorize call must NOT succeed using the denied grant —
            # it should create a NEW pending request instead.
            status, resp_msg2_retry = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg2}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp_msg2_retry.get('needsElevation') is True, (
                f'denied grant must not be reused; must return needsElevation: {resp_msg2_retry}'
            )
            assert resp_msg2_retry.get('requestId') != request_id_2, (
                'a NEW elevation request must be created after a denied one',
                resp_msg2_retry,
            )

            # ─── Scenario 6: Host-only authorization ───────────────────────
            # A non-host (a freshly registered user with no invitation access)
            # must NOT be able to approve or deny JIT requests for the host's
            # invitations.
            email_outsider = 'sec5-jit-outsider@example.com'
            _, auth_out = http_json(base, '/api/auth/register', 'POST',
                                   {'email': email_outsider, 'password': password}, expected=201)
            token_outsider = auth_out['token']
            # Create a new pending request for the host.
            msg_call_3 = make_tool_call(
                server, 'message.prepare_send',
                {'channel': 'email', 'recipientIds': ['guest-3'], 'message': 'Outsider test'},
                reason='Test outsider deny',
            )
            plan_id_msg3 = create_confirmed_plan(
                service, invite_id, host_id, 'owner', [msg_call_3], 'sec5-jit-msg3-plan',
            )
            status, resp_msg3 = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg3}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp_msg3.get('needsElevation') is True, resp_msg3
            request_id_3 = resp_msg3['requestId']
            # Outsider attempts to approve → 403.
            status, err_out = http_json(
                base, '/api/ai-agent/jit/approve', 'POST',
                {'request_id': request_id_3}, token_outsider, expected=None,
            )
            assert status == 403, f'outsider approve must be 403; got {status}: {err_out}'
            assert err_out.get('code') == 'jit_not_host', err_out
            # Outsider attempts to deny → 403.
            status, err_out_d = http_json(
                base, '/api/ai-agent/jit/deny', 'POST',
                {'request_id': request_id_3, 'reason': 'outsider'}, token_outsider, expected=None,
            )
            assert status == 403, f'outsider deny must be 403; got {status}: {err_out_d}'
            # The elevation row is still 'requested' (the outsider's calls were rejected).
            elev_unchanged = service.jit.get_elevation(request_id_3)
            assert elev_unchanged['status'] == 'requested', elev_unchanged

            # ─── Scenario 7: Audit events ──────────────────────────────────
            # Verify the hash-chained audit_events table captured the JIT
            # lifecycle events for the host user.
            actions = fetch_audit_actions(server, host_id)
            assert 'jit.requested' in actions, actions
            assert 'jit.granted' in actions, actions
            assert 'jit.consumed' in actions, actions
            assert 'jit.denied' in actions, actions
            assert 'jit.expired' in actions, actions

            # ─── Scenario 8: Negative proof (disabling JIT breaks the contract) ──
            # Monkey-patch JITElevationManager.evaluate to return True (the old
            # Phase 1a stub). The manual-approval tool must now succeed WITHOUT
            # elevation — proving that the JIT enforcement is load-bearing.
            # If a future refactor accidentally re-introduces the stub, the
            # main scenarios above will fail (they assert needsElevation).
            msg_call_4 = make_tool_call(
                server, 'message.prepare_send',
                {'channel': 'email', 'recipientIds': ['guest-4'], 'message': 'Negative proof'},
                reason='Negative proof test',
            )
            plan_id_msg4 = create_confirmed_plan(
                service, invite_id, host_id, 'owner', [msg_call_4], 'sec5-jit-msg4-plan',
            )
            with mock.patch.object(
                server.JITElevationManager, 'evaluate', return_value=True,
            ):
                status, resp_neg = http_json(
                    base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg4}/authorize',
                    'POST', {'index': 0, 'context': {}}, token_host, expected=200,
                )
                # With JIT enforcement disabled, the call must succeed
                # immediately — NO needsElevation response.
                assert resp_neg.get('authorized') is True, (
                    f'with JIT disabled, authorize must succeed; got: {resp_neg}'
                )
                assert 'needsElevation' not in resp_neg, (
                    f'with JIT disabled, no needsElevation; got: {resp_neg}'
                )
            # Sanity: after the patch is removed, the same call must return
            # needsElevation again (proves the patch was scoped + the wiring
            # is back in force).
            msg_call_5 = make_tool_call(
                server, 'message.prepare_send',
                {'channel': 'email', 'recipientIds': ['guest-5'], 'message': 'After patch'},
                reason='After-patch test',
            )
            plan_id_msg5 = create_confirmed_plan(
                service, invite_id, host_id, 'owner', [msg_call_5], 'sec5-jit-msg5-plan',
            )
            status, resp_after = http_json(
                base, f'/api/invitations/{invite_id}/ai/plans/{plan_id_msg5}/authorize',
                'POST', {'index': 0, 'context': {}}, token_host, expected=200,
            )
            assert resp_after.get('needsElevation') is True, (
                f'after removing the monkey-patch, JIT must be enforced again; got: {resp_after}'
            )

        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)

    print('AI_JIT_ENFORCEMENT_TEST_PASSED')
    return 0


# pytest-compatible entry point.
def test_ai_jit_enforcement():
    run()


if __name__ == '__main__':
    raise SystemExit(run())
