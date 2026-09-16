#!/usr/bin/env python3
"""Phase 2a (V54.1) — Multi-channel delivery abstraction contract test.

Two-part test:

1. **Unit-level** — exercise the delivery_channels package directly:
   registry returns the right channels, email channel is available because
   ``register_email_sender`` was wired, SMS/WhatsApp/Telegram degrade
   gracefully when env is unset, SendResult never raises.

2. **HTTP-level** — exercise the full server:
   - ``GET /api/invitations/{id}/delivery-channels`` returns the metadata list.
   - ``POST /api/invitations/{id}/deliver`` with channels=['email','sms','whatsapp','telegram']
     for a guest with both email and phone: email queued, others skipped
     (env not set), delivery_attempts table records all four attempts.
   - ``GET /api/invitations/{id}/deliveries`` lists attempts.
"""
from __future__ import annotations
import json
import os
import sys
import urllib.request
import urllib.error
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'python'))


def run_unit():
    """Test the delivery_channels package directly."""
    from delivery_channels import get_channel, available_channels, channel_metadata, register_email_sender

    # Wire a fake sender so the email channel reports available.
    sent = []
    register_email_sender(lambda to, subject, body: sent.append((to, subject, body)) or True)
    channels = available_channels()
    assert 'email' in channels, f'email should be available after register_email_sender, got: {channels}'

    # Email send — should call the wired sender.
    email = get_channel('email')
    result = email.send('inv-1', 'guest@example.com', 'Hello', {'subject': 'Invite'})
    assert result.status == 'sent', f'expected sent, got: {result}'
    assert result.provider_message_id == 'smtp'
    assert sent and sent[0][0] == 'guest@example.com'

    # SMS without env — should be skipped.
    sms = get_channel('sms')
    assert not sms.available(), 'sms should not be available without env'
    r2 = sms.send('inv-1', '+15551234567', 'Hello', {})
    assert r2.status == 'skipped', f'expected skipped, got: {r2.status}'

    # WhatsApp without env — should be skipped.
    wa = get_channel('whatsapp')
    assert not wa.available()
    r3 = wa.send('inv-1', '+15551234567', 'Hello', {})
    assert r3.status == 'skipped'

    # Telegram without env — should be skipped.
    tg = get_channel('telegram')
    assert not tg.available()
    r4 = tg.send('inv-1', '1234567', 'Hello', {})
    assert r4.status == 'skipped'

    # Channel metadata exposes bilingual labels.
    meta = channel_metadata()
    assert isinstance(meta, list) and len(meta) == 4
    email_meta = next(m for m in meta if m['name'] == 'email')
    assert email_meta['label_km'] == 'អ៊ីមែល', f'expected Khmer label, got: {email_meta["label_km"]}'

    # SendResult never raises even on bogus input.
    r5 = email.send('inv-1', '', '', {})
    assert r5.status == 'skipped'

    # Now configure SMS env vars and verify availability flips.
    os.environ['EINVITE_SMS_ACCOUNT_SID'] = 'AC' + '0' * 32
    os.environ['EINVITE_SMS_AUTH_TOKEN'] = 'abc123'
    os.environ['EINVITE_SMS_FROM'] = '+15550000000'
    sms2 = type(sms)()  # Re-instantiate to pick up env.
    assert sms2.available(), f'sms should be available with env, got available={sms2.available()}'
    # The actual send will fail (no real Twilio backend) but SendResult must not raise.
    r6 = sms2.send('inv-1', '+15551234567', 'Hello', {})
    assert r6.status in {'sent', 'queued', 'failed'}, f'unexpected status: {r6.status}'
    # Clean up.
    for k in ('EINVITE_SMS_ACCOUNT_SID', 'EINVITE_SMS_AUTH_TOKEN', 'EINVITE_SMS_FROM'):
        del os.environ[k]

    print('P2A_DELIVERY_CHANNELS_UNIT_TEST_PASSED')


class Client:
    def __init__(self, base):
        self.base = base
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.token = ''

    def request(self, path, method='GET', body=None, expected=200, headers=None):
        payload = None if body is None else json.dumps(body).encode('utf-8')
        hdr = {'Accept': 'application/json', **(headers or {})}
        if payload is not None: hdr['Content-Type'] = 'application/json'
        if self.token: hdr['Authorization'] = f'Bearer {self.token}'
        req = urllib.request.Request(self.base + path, data=payload, method=method, headers=hdr)
        try:
            with self.opener.open(req, timeout=15) as response:
                status = response.status; raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code; raw = exc.read()
        if status != expected:
            raise AssertionError(f'{method} {path}: expected {expected}, got {status}: {raw[:500]!r}')
        return json.loads(raw or b'{}')


def run_http():
    """Test the server's /api/invitations/{id}/deliver flow."""
    from v14_test_utils import app_server
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION': '0',
                     'EINVITE_ALLOW_NO_SCANNER': '1'}) as (_process, base, _data):
        client = Client(base)
        registered = client.request('/api/auth/register', 'POST',
                                     {'email': 'p2a-deliver@example.com', 'password': 'strong-password-123'}, 201)
        client.token = registered.get('token', '')

        doc = {'schemaVersion': 13, 'eventType': 'Wedding',
               'fields': {'names': 'Deliver Couple', 'date': '2027-07-14', 'venue': 'Deliver Hall'},
               'objects': {}, 'designPages': [], 'sectionOrder': [],
               'settings': {'rsvpEnabled': False, 'wishesEnabled': False}}
        invitation = client.request('/api/invitations', 'POST', {'slug': 'p2a-deliver-test', 'document': doc}, 201)
        invite_id = invitation['id']
        client.request(f'/api/invitations/{invite_id}/publish', 'POST', {'document': doc}, 201)

        # Add a guest with both email and phone.
        guest = client.request(f'/api/invitations/{invite_id}/guests', 'POST', {
            'name': 'Multi Channel', 'email': 'multi@example.com', 'phone': '+15551234567',
        }, 201)

        # List configured channels (email only in test env).
        channels = client.request(f'/api/invitations/{invite_id}/delivery-channels')
        names = [c['name'] for c in channels['channels']]
        assert 'email' in names
        assert 'sms' in names  # always registered, but available=False
        assert 'whatsapp' in names
        assert 'telegram' in names
        email_meta = next(c for c in channels['channels'] if c['name'] == 'email')
        # Email may be 'configured' or not depending on whether SMTP is set.
        # In the test env it's not set, so we just check the metadata shape.
        assert 'label_en' in email_meta and 'label_km' in email_meta

        # Deliver via all four channels — only email should attempt (others skipped).
        deliver = client.request(f'/api/invitations/{invite_id}/deliver', 'POST', {
            'channels': ['email', 'sms', 'whatsapp', 'telegram'],
            'recipients': [{
                'guestId': guest['id'],
                'name': 'Multi Channel',
                'email': 'multi@example.com',
                'phone': '+15551234567',
            }],
            'message': 'You are invited via multiple channels!',
            'subject': 'Multi-channel test',
        }, 200)
        results = deliver['results']
        assert len(results) == 4, f'expected 4 results, got {len(results)}'
        by_channel = {r['channel']: r for r in results}
        # Email: queued (no SMTP in test env) — accept sent or queued.
        assert by_channel['email']['status'] in {'sent', 'queued'}, f'expected email queued/sent, got: {by_channel["email"]}'
        # SMS / WhatsApp / Telegram: skipped (env not configured).
        for ch in ('sms', 'whatsapp', 'telegram'):
            assert by_channel[ch]['status'] == 'skipped', f'expected {ch} skipped, got: {by_channel[ch]["status"]}'

        # Verify delivery_attempts table records all four.
        deliveries = client.request(f'/api/invitations/{invite_id}/deliveries')
        assert deliveries['total'] == 4, f'expected 4 delivery_attempts, got: {deliveries["total"]}'
        # Verify sent_at is set on the invitation (post-send edit-history wedge).
        # (The list_deliveries endpoint doesn't return invitation fields; we
        # rely on the post-send-editing test to verify sent_at directly.)

        # Verify error path: invalid channel.
        try:
            client.request(f'/api/invitations/{invite_id}/deliver', 'POST', {
                'channels': ['fax'], 'recipients': [{'email': 'x@example.com'}],
            }, 400)
        except AssertionError as exc:
            raise AssertionError(f'Expected 400 for unsupported channel, got: {exc}')

        # Verify error path: missing recipients.
        try:
            client.request(f'/api/invitations/{invite_id}/deliver', 'POST', {
                'channels': ['email'], 'recipients': [],
            }, 400)
        except AssertionError as exc:
            raise AssertionError(f'Expected 400 for empty recipients, got: {exc}')

    print('P2A_DELIVERY_CHANNELS_HTTP_TEST_PASSED')


def run():
    run_unit()
    run_http()


if __name__ == '__main__':
    run()
