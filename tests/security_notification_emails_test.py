#!/usr/bin/env python3
"""V54.10 (SEC-4 — P1-D) — Security notification emails on MFA/passkey/password changes.

Real-HTTP integration test running an in-process ThreadingHTTPServer so that
``unittest.mock.patch`` can intercept ``server.send_platform_email`` calls
made by the request-handler thread (same Python process → same module
namespace → patched name is visible to the handler).

Coverage matrix:
  - mfa.enabled     → send_security_notification fires, subject contains
                       "MFA enabled" + Khmer variant "MFA បានបើក".
  - mfa.disabled    → subject contains "MFA disabled" + "MFA បានបិទ".
  - passkey.added   → subject contains "passkey was added" + Khmer variant.
                       (WebAuthn crypto bypassed by patching the three
                       verifier helpers in the server namespace — the
                       notification wiring itself is what we are testing,
                       not the attestation parser.)
  - passkey.removed → subject contains "passkey was removed" + Khmer variant.
  - password.changed → subject contains "password was changed" + Khmer variant.
  - SMTP-not-configured fallback: when send_platform_email raises, the
                       underlying security state change (mfa_enable) still
                       returns 200 — the helper logs and continues, no
                       exception propagates to the caller.

Acceptance: prints ``SECURITY_NOTIFICATION_EMAILS_TEST_PASSED`` on success.
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
        with urllib.request.urlopen(req, timeout=15) as response:
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


def totp_now(security_v13, secret):
    """Compute the current TOTP code for a base32 secret."""
    counter = security_v13._totp_counter()
    return security_v13.totp_code(secret, counter)


def run_success_flow(server, security_v13, hashlib_mod, base, sent_emails):
    """Cover all five event types with send_platform_email succeeding."""
    # --- Register a fresh user ---
    _, auth = http_json(base, '/api/auth/register', 'POST',
                       {'email': 'sec4-user@example.com', 'password': 'StrongPassw0rd!'},
                       expected=201)
    token = auth['token']
    user_email = auth['user']['email']
    assert token, 'dev bearer token missing'

    # --- MFA setup ---
    _, setup = http_json(base, '/api/account/mfa/setup', 'POST', {}, token, expected=200)
    secret = setup['secret']
    assert secret, 'mfa secret missing'

    # --- mfa.enabled ---
    code = totp_now(security_v13, secret)
    _, enabled = http_json(base, '/api/account/mfa/enable', 'POST', {'code': code},
                           token, expected=200)
    assert enabled['enabled'] is True
    last = sent_emails[-1]
    assert last['to'] == user_email, last
    assert 'MFA enabled' in last['subject'], last['subject']
    assert 'MFA បានបើក' in last['subject'], last['subject']
    assert '/account/security' in last['body'], 'body missing wasn\'t-me link'
    assert 'IP address:' in last['body'], 'body missing IP line'
    assert 'Device / browser:' in last['body'], 'body missing UA line'

    # --- mfa.disabled (need a fresh TOTP code) ---
    # Tiny sleep so we don't accidentally reuse the same counter (rare but possible).
    time.sleep(0.05)
    code2 = totp_now(security_v13, secret)
    _, disabled = http_json(base, '/api/account/mfa/disable', 'POST', {'code': code2},
                            token, expected=200)
    assert disabled['enabled'] is False
    last = sent_emails[-1]
    assert 'MFA disabled' in last['subject'], last['subject']
    assert 'MFA បានបិទ' in last['subject'], last['subject']
    # Stronger warning text should appear in the MFA-disabled body.
    assert 're-enable MFA' in last['body'] or 'បើក MFA' in last['body'], last['body']

    # --- password.changed ---
    _, changed = http_json(base, '/api/auth/password', 'PUT',
                          {'currentPassword': 'StrongPassw0rd!',
                           'newPassword': 'EvenStrongerPassw0rd!!'},
                          token, expected=200)
    assert changed['changed'] is True
    last = sent_emails[-1]
    assert 'password was changed' in last['subject'].lower(), last['subject']
    assert 'ពាក្យសម្ងាត់' in last['subject'], last['subject']

    # --- passkey.added (WebAuthn crypto bypassed via mock) ---
    _, opts = http_json(base, '/api/account/passkeys/register/options', 'POST',
                       {}, token, expected=200)
    challenge_id = opts['challengeId']
    rp_id = '127.0.0.1'  # bound to 127.0.0.1:port, COOKIE_SECURE=0
    rp_hash = hashlib_mod.sha256(rp_id.encode()).digest()
    # authData: rp_id_hash (32) + flags byte (0x01 = UP) + signCount(4) + aaguid(16) + credLen(2) + credId(32)
    fake_auth_data = rp_hash + bytes([0x01]) + b'\x00\x00\x00\x01' + b'\x00' * 16 + b'\x00\x20' + b'A' * 32
    fake_parsed = {
        'authData': fake_auth_data,
        'credentialId': b'cred-id-bytes-1234',
        'coseKey': {'fake': True},
        'signCount': 1,
    }
    with mock.patch.object(server, 'verify_client_data',
                           return_value=(b'raw-client-data', {})), \
         mock.patch.object(server, 'parse_attestation_object',
                           return_value=fake_parsed), \
         mock.patch.object(server, 'cose_ec2_to_pem',
                           return_value='-----BEGIN PUBLIC KEY-----\nFAKE\n-----END PUBLIC KEY-----\n'):
        _, reg = http_json(base, '/api/account/passkeys/register/complete', 'POST',
                          {'challengeId': challenge_id,
                           'name': 'Test Passkey',
                           'credential': {'id': 'cred-id',
                                          'transports': ['internal'],
                                          'response': {'clientDataJSON': 'x',
                                                       'attestationObject': 'y'}}},
                          token, expected=201)
    assert reg['registered'] is True
    last = sent_emails[-1]
    assert 'passkey was added' in last['subject'].lower(), last['subject']
    assert 'Passkey បានបន្ថែម' in last['subject'], last['subject']

    # --- passkey.removed ---
    _, keys = http_json(base, '/api/account/passkeys', 'GET', None, token, expected=200)
    assert len(keys) >= 1, keys
    key_id = keys[0]['id']
    _, deleted = http_json(base, f'/api/account/passkeys/{key_id}', 'DELETE',
                           None, token, expected=200)
    assert deleted['deleted'] is True
    last = sent_emails[-1]
    assert 'passkey was removed' in last['subject'].lower(), last['subject']
    assert 'Passkey បានដកចេញ' in last['subject'], last['subject']

    return token


def run_smtp_failure_flow(server, security_v13, base, sent_emails):
    """When send_platform_email raises, the security state change still succeeds."""
    # Re-setup MFA — the user already exists from the success flow.
    # Re-register a fresh user to avoid any leftover state confusion.
    _, auth = http_json(base, '/api/auth/register', 'POST',
                       {'email': 'sec4-user2@example.com', 'password': 'StrongPassw0rd!'},
                       expected=201)
    token = auth['token']
    _, setup = http_json(base, '/api/account/mfa/setup', 'POST', {}, token, expected=200)
    secret = setup['secret']

    before = len(sent_emails)
    code = totp_now(security_v13, secret)
    # send_platform_email is currently configured to raise via side_effect.
    _, enabled = http_json(base, '/api/account/mfa/enable', 'POST', {'code': code},
                           token, expected=200)
    assert enabled['enabled'] is True, 'mfa_enable should still succeed when SMTP raises'
    # No new emails captured (since the helper swallowed the exception).
    assert len(sent_emails) == before, (
        f'SMTP-failure flow should not have captured new emails: {sent_emails[before:]}'
    )

    # Also verify password change path is resilient.
    before2 = len(sent_emails)
    _, changed = http_json(base, '/api/auth/password', 'PUT',
                          {'currentPassword': 'StrongPassw0rd!',
                           'newPassword': 'AnotherStrongPass!!'},
                          token, expected=200)
    assert changed['changed'] is True, 'password change should still succeed when SMTP raises'
    assert len(sent_emails) == before2, 'password.changed should not have sent when SMTP raises'


def main():
    import hashlib as hashlib_mod
    with tempfile.TemporaryDirectory(prefix='einvite-sec4-notif-') as data_dir:
        os.environ['EINVITE_DATA_DIR'] = data_dir
        import server  # noqa: E402  (import after env vars are set)
        from core import auth as security_v13  # noqa: E402

        sent_emails = []

        def fake_send(to_email, subject, body):
            sent_emails.append({'to': to_email, 'subject': subject, 'body': body})
            return True

        def raising_send(to_email, subject, body):
            raise RuntimeError('SMTP not configured (simulated)')

        # --- Phase A: success path (send_platform_email returns True) ---
        with mock.patch.object(server, 'send_platform_email', side_effect=fake_send):
            port = free_port()
            httpd = server.ThreadingHTTPServer(('127.0.0.1', port), server.Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{port}'
            try:
                run_success_flow(server, security_v13, hashlib_mod, base, sent_emails)
                # Sanity check: at least 5 notifications captured (mfa.enabled,
                # mfa.disabled, password.changed, passkey.added, passkey.removed).
                assert len(sent_emails) >= 5, (
                    f'expected ≥5 sent emails, got {len(sent_emails)}: {sent_emails}'
                )

                # --- Phase B: SMTP-not-configured fallback ---
                # Switch the patched Mock's side_effect to raise. The handler
                # thread still sees the same module-level name, so the new
                # side_effect takes effect immediately for in-flight requests.
                server.send_platform_email.side_effect = raising_send
                run_smtp_failure_flow(server, security_v13, base, sent_emails)
            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=3)

    print('SECURITY_NOTIFICATION_EMAILS_TEST_PASSED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
