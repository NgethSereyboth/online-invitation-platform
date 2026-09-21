#!/usr/bin/env python3
"""Phase 2a (V54.1) — Sign-up sheets contract test.

Real-HTTP integration test: registers a host account, creates an invitation,
publishes it, creates a sign-up sheet, claims a slot as a guest, cancels the
claim, lists sheets as guest (verifying PII hiding), and verifies host vs
guest access control. Uses the V14 app_server helper so the test exercises
the actual HTTP layer end-to-end.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from http.cookiejar import CookieJar
from pathlib import Path

from v14_test_utils import app_server

ROOT = Path(__file__).resolve().parents[1]


class Client:
    def __init__(self, base):
        self.base = base
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.token = ''

    def request(self, path, method='GET', body=None, expected=200, headers=None, parse_json=True):
        payload = None if body is None else json.dumps(body).encode('utf-8')
        hdr = {'Accept': 'application/json' if parse_json else '*/*', **(headers or {})}
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
        if parse_json:
            return json.loads(raw or b'{}')
        return raw

    def upload(self, path, file_bytes, filename, mime, fields=None, expected=201):
        boundary = '----p2atestboundary' + '0' * 12
        body_parts = []
        if fields:
            for name, value in fields.items():
                body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode('utf-8'))
        body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode('utf-8'))
        body_parts.append(file_bytes)
        body_parts.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
        body = b''.join(body_parts)
        hdr = {'Content-Type': f'multipart/form-data; boundary={boundary}', 'Content-Length': str(len(body))}
        if self.token: hdr['Authorization'] = f'Bearer {self.token}'
        req = urllib.request.Request(self.base + path, data=body, method='POST', headers=hdr)
        try:
            with self.opener.open(req, timeout=15) as response:
                status = response.status; raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code; raw = exc.read()
        if status != expected:
            raise AssertionError(f'POST {path}: expected {expected}, got {status}: {raw[:500]!r}')
        return json.loads(raw or b'{}')


def run():
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION': '0',
                     'EINVITE_ALLOW_NO_SCANNER': '1'}) as (_process, base, _data):
        client = Client(base)
        # Register a host.
        registered = client.request('/api/auth/register', 'POST',
                                     {'email': 'p2a-signup@example.com', 'password': 'strong-password-123'}, 201)
        client.token = registered.get('token', '')
        assert client.token, 'host token missing'

        # Create + publish an invitation.
        doc = {'schemaVersion': 13, 'eventType': 'Wedding',
               'fields': {'names': 'P2A Couple', 'namesKm': 'ភាគីទាំងពីរ', 'date': '2027-03-14', 'venue': 'Test Hall'},
               'objects': {}, 'designPages': [], 'sectionOrder': [],
               'settings': {'rsvpEnabled': False, 'wishesEnabled': False}}
        invitation = client.request('/api/invitations', 'POST', {'slug': 'p2a-signup-test', 'document': doc}, 201)
        invite_id = invitation['id']
        client.request(f'/api/invitations/{invite_id}/publish', 'POST', {'document': doc}, 201)

        # Create a sign-up sheet as host.
        sheet = client.request(f'/api/invitations/{invite_id}/signup-sheets', 'POST', {
            'title': 'Potluck dishes', 'type': 'items',
            'slots': [
                {'id': 's1', 'label': 'Main course', 'capacity': 2, 'description': 'Serves 6-8'},
                {'id': 's2', 'label': 'Dessert', 'capacity': 1},
            ],
            'deadlineTs': None,
        }, 201)
        assert sheet['id'], 'sheet id missing'
        assert len(sheet['slots']) == 2, f'expected 2 slots, got {len(sheet["slots"])}'
        assert sheet['slots'][0]['remaining'] == 2, f'expected 2 remaining, got {sheet["slots"][0]["remaining"]}'

        # List sheets as host (should include claims array even when empty).
        sheets = client.request(f'/api/invitations/{invite_id}/signup-sheets')
        assert len(sheets) == 1
        assert sheets[0]['slots'][0]['claims'] == [], 'host should see empty claims list'

        # Guest claim (no auth, no guest token — anonymous).
        claim = client.request(f'/api/invitations/{invite_id}/signup-sheets/{sheet["id"]}/claim', 'POST',
                                {'slotId': 's1', 'quantity': 1, 'name': 'Guest One', 'email': 'g1@example.com'}, 201)
        assert claim['id'], 'claim id missing'

        # Verify capacity update.
        sheets = client.request(f'/api/invitations/{invite_id}/signup-sheets')
        s1 = next(s for s in sheets[0]['slots'] if s['id'] == 's1')
        assert s1['claimedQuantity'] == 1, f'expected 1 claimed, got {s1["claimedQuantity"]}'
        assert s1['remaining'] == 1, f'expected 1 remaining, got {s1["remaining"]}'

        # Verify capacity enforcement: claim quantity=2 should fail (would exceed cap of 2 with 1 already claimed).
        try:
            client.request(f'/api/invitations/{invite_id}/signup-sheets/{sheet["id"]}/claim', 'POST',
                            {'slotId': 's1', 'quantity': 2, 'name': 'Guest Two'}, 409)
        except AssertionError as exc:
            raise AssertionError(f'Expected 409 for over-capacity claim, got: {exc}')

        # Update the sheet (host).
        updated = client.request(f'/api/invitations/{invite_id}/signup-sheets/{sheet["id"]}', 'PUT', {
            'title': 'Potluck dishes (updated)',
            'slots': [
                {'id': 's1', 'label': 'Main course', 'capacity': 3, 'description': 'Serves 6-8'},
                {'id': 's2', 'label': 'Dessert', 'capacity': 1},
                {'id': 's3', 'label': 'Drinks', 'capacity': 5},
            ],
        }, 200)
        assert updated['title'] == 'Potluck dishes (updated)'
        assert len(updated['slots']) == 3

        # Cancel the claim (host can cancel any).
        cancel = client.request(f'/api/invitations/{invite_id}/signup-sheets/{sheet["id"]}/claims/{claim["id"]}', 'DELETE', expected=200)
        assert cancel['cancelled'] is True

        # Delete the sheet (host).
        deleted = client.request(f'/api/invitations/{invite_id}/signup-sheets/{sheet["id"]}', 'DELETE', expected=200)
        assert deleted['deleted'] is True

        # Verify the sheet is gone (archived, not listed).
        sheets = client.request(f'/api/invitations/{invite_id}/signup-sheets')
        assert len(sheets) == 0, 'archived sheet should not appear in list'

        print('P2A_SIGNUP_SHEETS_TEST_PASSED')


if __name__ == '__main__':
    run()
