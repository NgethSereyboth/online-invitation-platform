#!/usr/bin/env python3
"""V54.11 (sec-2, P1-B from ASVS L2 gap analysis §2.2) — Per-account login lockout.

Real-HTTP integration test that exercises the sliding-window failed-login
counter + lockout lifecycle:

1.  Register a user with a known password.
2.  Make 5 failed login attempts (wrong password) → every attempt returns
    HTTP 401 (the server must NOT reveal that an account is being throttled).
3.  Inspect the SQLite ``users`` row directly: ``failed_login_attempts == 5``
    and ``locked_until`` is in the future.
4.  Verify ``login.account_locked`` audit event was emitted exactly once
    when the 5th failure triggered the lock.
5.  6th attempt with the CORRECT password → returns HTTP 423 with
    ``code == "account_locked"`` and a bilingual EN+KH message body.
6.  6th attempt with the WRONG password → also returns 423 (still locked).
7.  Manually clear the lockout in the DB (``locked_until = 0``) and attempt
    the CORRECT password → returns HTTP 201 (success), counter reset to 0,
    ``locked_until`` cleared.
8.  Sliding-window test: trigger one failed login, then jump the burst-start
    timestamp back 16 minutes in the DB, then trigger another failure → the
    counter must reset to 1 (NOT increment to 2).
9.  Persistence across server restart: trigger a fresh lockout, stop the
    server, start a second server pointing at the same DB file → the lock
    is still enforced (login returns 423).

Acceptance: prints ``SECURITY_ACCOUNT_LOCKOUT_TEST_PASSED`` on success.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

from v14_test_utils import app_server, temporary_data

ROOT = Path(__file__).resolve().parents[1]
DB_FILENAME = "invites.db"


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def http_json(base, path, method='GET', body=None, token=None,
              expected=None):
    """Issue a JSON request; return (status, payload). If ``expected`` is set
    and the status doesn't match, raise ``AssertionError``."""
    data = None if body is None else json.dumps(body).encode('utf-8')
    headers = {'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    payload = json.loads(raw or b'{}')
    if expected is not None and status != expected:
        raise AssertionError(
            f'{method} {path}: expected {expected}, got {status}: {payload}'
        )
    return status, payload


def open_db(data_dir: Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(data_dir / DB_FILENAME))
    db.row_factory = sqlite3.Row
    return db


def fetch_user(db, email):
    return db.execute(
        'SELECT failed_login_attempts, failed_login_first_at, locked_until '
        'FROM users WHERE email=?', (email,)).fetchone()


def count_audit(db, action, user_id=None):
    if user_id:
        row = db.execute(
            'SELECT COUNT(*) c FROM audit_events WHERE action=? AND user_id=?',
            (action, user_id)).fetchone()
    else:
        row = db.execute(
            'SELECT COUNT(*) c FROM audit_events WHERE action=?',
            (action,)).fetchone()
    return int(row['c']) if row else 0


def assert_eq(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f'{label}: expected {expected!r}, got {actual!r}')


EMAIL = 'sec2-lockout@example.com'
PASSWORD = 'StrongPassw0rd!-lockout-2'
WRONG = 'this-is-the-wrong-password-XYZ'


def run_lockout_lifecycle(base, data):
    """Phases 1-7: register, fail 5x, verify lock + audit, unlock, succeed."""
    http_json(base, '/api/auth/register', 'POST',
              {'email': EMAIL, 'password': PASSWORD}, expected=201)

    # 5 failed attempts — all 401.
    for i in range(5):
        status, body = http_json(base, '/api/auth/login', 'POST',
                                {'email': EMAIL, 'password': WRONG})
        assert_eq(status, 401, f'failed attempt {i + 1} status')
        assert 'account_locked' not in body, (
            f'failed attempt {i + 1} leaked lockout: {body}')

    with open_db(data) as db:
        user = fetch_user(db, EMAIL)
        assert user is not None, 'user row missing'
        assert_eq(int(user['failed_login_attempts']), 5,
                  'failed_login_attempts after 5 failures')
        locked_until = user['locked_until']
        assert locked_until is not None, (
            'locked_until must be set after 5 failures')
        now_ms = int(time.time() * 1000)
        assert int(locked_until) > now_ms, (
            f'locked_until {locked_until} should be in the future '
            f'(now={now_ms})')

        user_row = db.execute(
            'SELECT id FROM users WHERE email=?', (EMAIL,)).fetchone()
        user_id = user_row['id']
        locked_events = count_audit(db, 'login.account_locked', user_id)
        assert_eq(locked_events, 1,
                  'login.account_locked audit event count')

    # 6th attempt with CORRECT password → 423 (locked, password not checked).
    status, body = http_json(base, '/api/auth/login', 'POST',
                            {'email': EMAIL, 'password': PASSWORD})
    assert_eq(status, 423, '6th attempt (correct password) status')
    assert_eq(body.get('code'), 'account_locked',
              '6th attempt response code')
    assert_eq(body.get('message_en'),
              'Account temporarily locked. Try again in 15 minutes or '
              'reset your password.',
              '6th attempt EN message')
    assert body.get('message_km'), (
        f'6th attempt KH message missing: {body}')
    assert_eq(body.get('locked_until'), int(locked_until),
              '6th attempt locked_until echoed')

    # 6th attempt with WRONG password → also 423 (still locked).
    status, body = http_json(base, '/api/auth/login', 'POST',
                            {'email': EMAIL, 'password': WRONG})
    assert_eq(status, 423, '6th attempt (wrong password) status')
    assert_eq(body.get('code'), 'account_locked',
              '6th attempt (wrong) response code')

    # Manually clear the lockout in DB (simulates password reset /
    # admin clear) and verify a successful login now succeeds. The task
    # spec recommends ``locked_until = 0`` (treated as "not locked"
    # because ``0 < now``). With ``locked_until = 0``, the lazy-clear
    # branch on the next attempt emits ``login.lockout_cleared`` and
    # resets all three columns; the subsequent successful login then
    # proceeds normally and does NOT emit another ``login.lockout_cleared``
    # (the in-memory row snapshot was refreshed by the lazy-clear).
    with open_db(data) as db:
        db.execute(
            'UPDATE users SET locked_until=0 WHERE email=?', (EMAIL,))
        db.commit()

    status, body = http_json(base, '/api/auth/login', 'POST',
                            {'email': EMAIL, 'password': PASSWORD},
                            expected=201)
    assert body.get('user', {}).get('email') == EMAIL, (
        f'login user payload missing email: {body}')

    with open_db(data) as db:
        user = fetch_user(db, EMAIL)
        assert_eq(int(user['failed_login_attempts']), 0,
                  'failed_login_attempts after successful login')
        assert user['locked_until'] is None, (
            'locked_until must be cleared (NULL) after successful login')
        assert user['failed_login_first_at'] is None, (
            'failed_login_first_at must be cleared after successful login')

        # The lazy-clear branch on the post-clear attempt MUST have
        # emitted ``login.lockout_cleared`` with reason=lazy_expiry —
        # this verifies the audit trail records the unlock event.
        cleared_events = count_audit(db, 'login.lockout_cleared', user_id)
        assert_eq(cleared_events, 1,
                  'login.lockout_cleared count after lazy clear + success')


def run_sliding_window(base, data):
    """Phase 8: 15-min sliding window resets the burst counter."""
    # Start a fresh burst with one failure.
    status, _ = http_json(base, '/api/auth/login', 'POST',
                         {'email': EMAIL, 'password': WRONG})
    assert_eq(status, 401, 'sliding-window first failure status')

    with open_db(data) as db:
        user = fetch_user(db, EMAIL)
        assert_eq(int(user['failed_login_attempts']), 1,
                  'sliding-window counter after 1 failure')
        first_at = user['failed_login_first_at']
        assert first_at is not None, (
            'failed_login_first_at must be set after a failure')

        # Jump the burst-start timestamp back 16 minutes — past the 15-min
        # window. The next failure must reset the counter to 1 (a fresh
        # burst), NOT increment to 2.
        jump = int(first_at) - (16 * 60 * 1000)
        db.execute(
            'UPDATE users SET failed_login_first_at=? WHERE email=?',
            (jump, EMAIL))
        db.commit()

    status, _ = http_json(base, '/api/auth/login', 'POST',
                         {'email': EMAIL, 'password': WRONG})
    assert_eq(status, 401, 'sliding-window post-jump failure status')

    with open_db(data) as db:
        user = fetch_user(db, EMAIL)
        assert_eq(int(user['failed_login_attempts']), 1,
                  'sliding-window counter after jump+failure (must reset to 1, '
                  'not increment to 2)')

    # Clean up the leftover state so the restart test starts fresh.
    with open_db(data) as db:
        db.execute(
            'UPDATE users SET failed_login_attempts=0, '
            'failed_login_first_at=NULL, locked_until=NULL WHERE email=?',
            (EMAIL,))
        db.commit()


def run_lockout_persists_restart():
    """Phase 9: lockout survives a server restart because it's persisted in DB.

    Uses an explicit ``temporary_data()`` directory and starts TWO
    ``app_server`` instances sequentially, both pointing at the same DB
    file via ``EINVITE_DATA_DIR``.
    """
    with temporary_data('einvite-sec2-restart-') as data:
        env_override = {
            'EINVITE_DATA_DIR': str(data),
            'EINVITE_ALLOW_NO_SCANNER': '1',
            'EINVITE_REQUIRE_EMAIL_VERIFICATION': '0',
        }

        # ── First server: trigger a fresh lockout ──────────────────────────
        with app_server(extra_env=env_override) as (_proc1, base1, _inner1):
            # Register with a fresh email so we don't pick up state from
            # the earlier phases (each app_server invocation above used
            # its own fresh temp dir, but this restart test reuses the
            # same DB across two servers).
            restart_email = 'sec2-restart@example.com'
            http_json(base1, '/api/auth/register', 'POST',
                      {'email': restart_email, 'password': PASSWORD},
                      expected=201)
            for _ in range(5):
                status, _ = http_json(base1, '/api/auth/login', 'POST',
                                      {'email': restart_email,
                                       'password': WRONG})
                assert_eq(status, 401, 'restart-phase failed attempt status')

            # Confirm the lock is set in DB.
            with open_db(data) as db:
                user = fetch_user(db, restart_email)
                assert user is not None, 'restart user row missing'
                assert_eq(int(user['failed_login_attempts']), 5,
                          'restart-phase counter after 5 failures')
                assert user['locked_until'] is not None, (
                    'restart-phase locked_until must be set')
                locked_until_value = int(user['locked_until'])

        # ── First server has stopped. The DB file survives on disk. ────────
        # ── Second server: same DB file, the lock must still be enforced ──
        with app_server(extra_env=env_override) as (_proc2, base2, _inner2):
            status, body = http_json(base2, '/api/auth/login', 'POST',
                                     {'email': 'sec2-restart@example.com',
                                      'password': PASSWORD})
            assert_eq(status, 423,
                      'restart-phase post-restart login status (lock must '
                      'persist across server restart)')
            assert_eq(body.get('code'), 'account_locked',
                      'post-restart response code')
            assert_eq(body.get('locked_until'), locked_until_value,
                      'post-restart locked_until must equal pre-restart value')

            # Clear lockout + verify success on the restarted server.
            with open_db(data) as db:
                db.execute(
                    'UPDATE users SET failed_login_attempts=0, '
                    'failed_login_first_at=NULL, locked_until=NULL '
                    'WHERE email=?', ('sec2-restart@example.com',))
                db.commit()

            status, _ = http_json(base2, '/api/auth/login', 'POST',
                                  {'email': 'sec2-restart@example.com',
                                   'password': PASSWORD}, expected=201)


def run():
    # Use an explicit data dir so the restart test can reuse the same DB
    # file across two server instances.
    with temporary_data('einvite-sec2-') as data:
        env_override = {
            'EINVITE_DATA_DIR': str(data),
            'EINVITE_ALLOW_NO_SCANNER': '1',
            'EINVITE_REQUIRE_EMAIL_VERIFICATION': '0',
        }
        with app_server(extra_env=env_override) as (_proc, base, _inner):
            run_lockout_lifecycle(base, data)
            run_sliding_window(base, data)

    run_lockout_persists_restart()

    print('SECURITY_ACCOUNT_LOCKOUT_TEST_PASSED')


# pytest-compatible entry point.
def test_account_lockout():
    run()


if __name__ == '__main__':
    run()
