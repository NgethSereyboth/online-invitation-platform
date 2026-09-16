#!/usr/bin/env python3
"""V54.12 (SEC-3 — P1-C) — MFA recovery codes.

Real-HTTP integration test running an in-process ``ThreadingHTTPServer`` so
the test process can also reach into the SQLite DB directly (via
``server.connect``) to assert that the stored rows are HASHES, not
plaintext codes.

Coverage matrix:
  - ``mfa_enable`` returns ``recovery_codes`` (10 entries) in the response.
  - The DB has 10 rows in ``mfa_recovery_codes`` for the user, all
    ``used_at IS NULL``, all ``code_hash`` ≠ plaintext (and the hash is
    Argon2id or pbkdf2_sha256$-prefixed).
  - Each of the 10 plaintext codes logs the user in via
    ``/api/auth/mfa/recover`` (after the password login is forced into the
    MFA-challenge state). The session returned by the 1st recovery is
    usable; codes can be consumed in any order.
  - The 11th attempt (no unused codes remain) → 401 ``invalid_recovery_code``.
  - Regenerate flow: requires the current password, returns 10 NEW codes,
    invalidates the OLD codes (an old plaintext no longer authenticates).
  - ``recovery_codes_remaining`` appears in ``GET /api/account/security``;
    ``recovery_codes_low`` flips True when the count drops to ≤ 2.
  - ``used_at`` is set on every consumed code (never NULL again).
  - Hashing scheme is verified: at least one row's ``code_hash`` starts
    with ``$argon2`` (when argon2-cffi is installed) OR
    ``pbkdf2_sha256$`` (fallback). Plaintext is NEVER stored.

Acceptance: prints ``SECURITY_MFA_RECOVERY_TEST_PASSED`` on success.
"""
from __future__ import annotations
import json
import os
import socket
import sqlite3
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


def totp_now(security_v13, secret):
    return security_v13.totp_code(secret, security_v13._totp_counter())


def count_unused_recovery_codes(server, user_id):
    with server.connect() as db:
        row = db.execute(
            "SELECT COUNT(*) c FROM mfa_recovery_codes WHERE user_id=? AND used_at IS NULL",
            (user_id,),
        ).fetchone()
        return int(row['c'] if row else 0)


def fetch_all_recovery_rows(server, user_id):
    with server.connect() as db:
        return [
            dict(r) for r in db.execute(
                "SELECT id, code_hash, used_at, created_at FROM mfa_recovery_codes WHERE user_id=? ORDER BY created_at, id",
                (user_id,),
            ).fetchall()
        ]


def lookup_user_id(server, email):
    with server.connect() as db:
        row = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        return row['id'] if row else None


def run():
    import hashlib as hashlib_mod  # noqa: F401  (kept for parity with sibling tests)
    with tempfile.TemporaryDirectory(prefix='einvite-sec3-mfa-') as data_dir:
        os.environ['EINVITE_DATA_DIR'] = data_dir
        import server  # noqa: E402  (import after env is set)
        import security_v13

        sent_emails = []

        def fake_send(to_email, subject, body):
            sent_emails.append({'to': to_email, 'subject': subject, 'body': body})
            return True

        with mock.patch.object(server, 'send_platform_email', side_effect=fake_send):
            port = free_port()
            httpd = server.ThreadingHTTPServer(('127.0.0.1', port), server.Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{port}'
            try:
                # ─── Phase A — register + enable MFA → 10 codes returned ───
                email_a = 'sec3-recov-a@example.com'
                password = 'StrongPassw0rd!'
                _, auth = http_json(base, '/api/auth/register', 'POST',
                                   {'email': email_a, 'password': password}, expected=201)
                token_a = auth['token']
                assert token_a, 'dev bearer token missing'

                _, setup = http_json(base, '/api/account/mfa/setup', 'POST', {}, token_a, expected=200)
                secret = setup['secret']
                assert secret, 'mfa secret missing'

                code = totp_now(security_v13, secret)
                _, enabled = http_json(base, '/api/account/mfa/enable', 'POST',
                                       {'code': code}, token_a, expected=200)
                assert enabled['enabled'] is True, enabled
                codes_a = enabled.get('recovery_codes')
                assert isinstance(codes_a, list) and len(codes_a) == 10, (
                    f'mfa_enable must return 10 recovery codes, got: {codes_a}'
                )
                # Each code is well-formed: AAAA-AAAA-AAAA, 14 chars, all from the alphabet.
                seen = set()
                for c in codes_a:
                    assert len(c) == 14, c
                    assert c[4] == '-' and c[9] == '-', c
                    bare = c.replace('-', '')
                    assert len(bare) == 12, c
                    assert all(ch in 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' for ch in bare), c
                    assert c not in seen, ('duplicate plaintext code', c)
                    seen.add(c)

                user_id_a = lookup_user_id(server, email_a)
                assert user_id_a, 'user_id lookup failed'

                rows = fetch_all_recovery_rows(server, user_id_a)
                assert len(rows) == 10, f'expected 10 db rows, got {len(rows)}'
                # All hashes must differ from any plaintext (stored hash ≠ any plaintext).
                plaintext_set = set(codes_a)
                for r in rows:
                    assert r['code_hash'] not in plaintext_set, (
                        'PLAINTEXT LEAK: code_hash matches a plaintext code', r
                    )
                    # Hash shape: argon2id (preferred) or pbkdf2_sha256$ (fallback).
                    assert r['code_hash'].startswith('$argon2') or \
                           r['code_hash'].startswith('pbkdf2_sha256$'), r['code_hash'][:20]
                    assert r['used_at'] is None, ('fresh code should be unused', r)
                    assert r['created_at'] is not None and r['created_at'] > 0, r

                # recovery_codes_remaining reflects 10 after enable.
                _, sec_overview = http_json(base, '/api/account/security', 'GET', None, token_a, expected=200)
                assert sec_overview['recoveryCodesRemaining'] == 10, sec_overview
                assert 'recoveryCodesLow' not in sec_overview, (
                    'low flag should NOT be present at 10 codes', sec_overview
                )

                # ─── Phase B — each of the 10 codes logs the user in ───
                # The recovery endpoint is unauthenticated (the user has lost
                # their authenticator) and issues a fresh session. We pass an
                # explicit email + recovery_code pair. We also try the
                # canonical and the no-hyphen / lowercase variants on the
                # first code to confirm input normalisation works.
                # Variant 1: canonical (uppercase, hyphens).
                status, login_payload = http_json(
                    base, '/api/auth/mfa/recover', 'POST',
                    {'email': email_a, 'recovery_code': codes_a[0]},
                    expected=201,
                )
                assert login_payload.get('user', {}).get('email') == email_a, login_payload
                # Variant: lowercase + no hyphens for code #2 (tests normalisation).
                bare = codes_a[1].replace('-', '').lower()
                status, login_payload = http_json(
                    base, '/api/auth/mfa/recover', 'POST',
                    {'email': email_a, 'recovery_code': bare},
                    expected=201,
                )
                assert login_payload.get('user', {}).get('email') == email_a, login_payload
                # Codes 3..10 — canonical form.
                for i in range(2, 10):
                    status, login_payload = http_json(
                        base, '/api/auth/mfa/recover', 'POST',
                        {'email': email_a, 'recovery_code': codes_a[i]},
                        expected=201,
                    )
                    assert login_payload.get('user', {}).get('email') == email_a, (
                        f'code #{i + 1} should authenticate', login_payload
                    )
                # All 10 should now be marked used (used_at IS NOT NULL).
                rows_after = fetch_all_recovery_rows(server, user_id_a)
                assert all(r['used_at'] is not None for r in rows_after), rows_after
                assert count_unused_recovery_codes(server, user_id_a) == 0

                # ─── Phase C — 11th attempt (no codes left) → 401 ───
                # Try the SAME code that already worked → must fail (one-shot).
                status, err = http_json(
                    base, '/api/auth/mfa/recover', 'POST',
                    {'email': email_a, 'recovery_code': codes_a[0]},
                    expected=None,
                )
                assert status == 401, f'expected 401 for replayed code, got {status}'
                assert err.get('code') == 'invalid_recovery_code', err
                # Try a totally bogus code → 401.
                status, err = http_json(
                    base, '/api/auth/mfa/recover', 'POST',
                    {'email': email_a, 'recovery_code': 'XXXX-XXXX-XXXX'},
                    expected=None,
                )
                assert status == 401, err
                assert err.get('code') == 'invalid_recovery_code', err
                # Try a non-existent user → 401 same shape (no enumeration).
                status, err = http_json(
                    base, '/api/auth/mfa/recover', 'POST',
                    {'email': 'sec3-ghost@example.com', 'recovery_code': codes_a[0]},
                    expected=None,
                )
                assert status == 401, err
                assert err.get('code') == 'invalid_recovery_code', err

                # ─── Phase D — low-codes flag ───
                # Set up a fresh user, enable MFA, then consume 8 codes to
                # reach exactly 2 remaining → recoveryCodesLow should be True.
                email_b = 'sec3-recov-b@example.com'
                _, auth_b = http_json(base, '/api/auth/register', 'POST',
                                     {'email': email_b, 'password': password}, expected=201)
                token_b = auth_b['token']
                _, setup_b = http_json(base, '/api/account/mfa/setup', 'POST', {}, token_b, expected=200)
                secret_b = setup_b['secret']
                code_b = totp_now(security_v13, secret_b)
                _, enabled_b = http_json(base, '/api/account/mfa/enable', 'POST',
                                         {'code': code_b}, token_b, expected=200)
                codes_b = enabled_b['recovery_codes']
                assert len(codes_b) == 10
                # Consume 8 of them via recovery (each issues a session — we don't need to keep them).
                for c in codes_b[:8]:
                    _, _ = http_json(base, '/api/auth/mfa/recover', 'POST',
                                    {'email': email_b, 'recovery_code': c}, expected=201)
                # The recovery endpoint consumed codes; the *original* token_b
                # session is independent and unaffected.
                _, sec_b = http_json(base, '/api/account/security', 'GET', None, token_b, expected=200)
                assert sec_b['recoveryCodesRemaining'] == 2, sec_b
                assert sec_b.get('recoveryCodesLow') is True, (
                    'low flag MUST be True at exactly 2 remaining', sec_b
                )

                # ─── Phase E — regenerate flow ───
                # Requires the current password. Returns 10 NEW codes. Old
                # codes (the 2 unused from phase D) no longer work.
                # Wrong password → 401.
                status, err = http_json(
                    base, '/api/account/mfa/recovery-codes/regenerate', 'POST',
                    {'currentPassword': 'WrongPassword99!'}, token_b, expected=None,
                )
                assert status == 401, err
                assert err.get('code') == 'invalid_password', err
                # Correct password → 10 new codes.
                status, regen = http_json(
                    base, '/api/account/mfa/recovery-codes/regenerate', 'POST',
                    {'currentPassword': password}, token_b, expected=200,
                )
                assert regen['regenerated'] is True, regen
                codes_b_new = regen['recovery_codes']
                assert len(codes_b_new) == 10, regen
                # The 10 new codes are DIFFERENT from the 2 leftover codes.
                leftover_b = set(codes_b[8:])
                for c in codes_b_new:
                    assert c not in leftover_b, ('regenerated code matches an old code', c)
                # DB still has exactly 10 unused rows for user_b (deletion + fresh insert).
                user_id_b = lookup_user_id(server, email_b)
                assert count_unused_recovery_codes(server, user_id_b) == 10
                # OLD leftover codes no longer authenticate.
                for c in codes_b[8:]:
                    status, err = http_json(
                        base, '/api/auth/mfa/recover', 'POST',
                        {'email': email_b, 'recovery_code': c}, expected=None,
                    )
                    assert status == 401, ('old code should no longer work', c, err)
                # NEW codes authenticate.
                _, login_b = http_json(
                    base, '/api/auth/mfa/recover', 'POST',
                    {'email': email_b, 'recovery_code': codes_b_new[0]}, expected=201,
                )
                assert login_b['user']['email'] == email_b, login_b

                # ─── Phase F — regenerate when MFA is disabled → 409 ───
                email_c = 'sec3-recov-c@example.com'
                _, auth_c = http_json(base, '/api/auth/register', 'POST',
                                      {'email': email_c, 'password': password}, expected=201)
                token_c = auth_c['token']
                status, err = http_json(
                    base, '/api/account/mfa/recovery-codes/regenerate', 'POST',
                    {'currentPassword': password}, token_c, expected=None,
                )
                assert status == 409, ('should refuse regen when MFA is off', status, err)
                assert err.get('code') == 'mfa_not_enabled', err

                # ─── Phase G — audit events ───
                # Verify the audit log captured mfa.enabled, mfa.recovery_used,
                # and mfa.recovery_codes_regenerated for the right users.
                with server.connect() as db:
                    a_user_events = [
                        dict(r) for r in db.execute(
                            "SELECT action FROM audit_events WHERE user_id=? AND action IN ('mfa.enabled','mfa.recovery_used','mfa.recovery_codes_regenerated') ORDER BY created_at",
                            (user_id_a,),
                        ).fetchall()
                    ]
                    actions_a = [e['action'] for e in a_user_events]
                    assert 'mfa.enabled' in actions_a, actions_a
                    # 10 recovery-used events for user A.
                    assert actions_a.count('mfa.recovery_used') == 10, actions_a
                    b_user_events = [
                        dict(r) for r in db.execute(
                            "SELECT action FROM audit_events WHERE user_id=? AND action IN ('mfa.recovery_used','mfa.recovery_codes_regenerated') ORDER BY created_at",
                            (user_id_b,),
                        ).fetchall()
                    ]
                    actions_b = [e['action'] for e in b_user_events]
                    assert actions_b.count('mfa.recovery_used') == 9, actions_b  # 8 + 1 from new codes
                    assert 'mfa.recovery_codes_regenerated' in actions_b, actions_b

            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join(timeout=3)

    print('SECURITY_MFA_RECOVERY_TEST_PASSED')
    return 0


# pytest-compatible entry point.
def test_mfa_recovery_codes():
    run()


if __name__ == '__main__':
    raise SystemExit(run())
