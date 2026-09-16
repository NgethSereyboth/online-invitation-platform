#!/usr/bin/env python3
"""Phase 2a (V54.1) — Post-send editing contract test.

End-to-end HTTP test: host creates invitation, delivers via email (queued
without SMTP), edits the invitation after sent_at is set, verifies the
invitation_edit_history row exists with the diff, hits the resend-notification
endpoint, verifies the "Edited at" badge data via the edit-history endpoint.
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


def run():
    with app_server({'EINVITE_REQUIRE_EMAIL_VERIFICATION': '0',
                     'EINVITE_ALLOW_NO_SCANNER': '1'}) as (_process, base, _data):
        client = Client(base)
        registered = client.request('/api/auth/register', 'POST',
                                     {'email': 'p2a-edit@example.com', 'password': 'strong-password-123'}, 201)
        client.token = registered.get('token', '')

        doc = {'schemaVersion': 13, 'eventType': 'Wedding',
               'fields': {'names': 'Edit Couple', 'date': '2027-06-14', 'venue': 'Original Venue'},
               'objects': {}, 'designPages': [], 'sectionOrder': [],
               'settings': {'rsvpEnabled': False, 'wishesEnabled': False}}
        invitation = client.request('/api/invitations', 'POST', {'slug': 'p2a-edit-test', 'document': doc}, 201)
        invite_id = invitation['id']
        client.request(f'/api/invitations/{invite_id}/publish', 'POST', {'document': doc}, 201)

        # Add a guest to deliver to.
        guest = client.request(f'/api/invitations/{invite_id}/guests', 'POST',
                                {'name': 'Edit Guest', 'email': 'edit-guest@example.com', 'phone': ''}, 201)

        # Deliver via email (SMTP not configured in test env → status='queued').
        deliver = client.request(f'/api/invitations/{invite_id}/deliver', 'POST', {
            'channels': ['email'],
            'recipients': [{'guestId': guest['id'], 'name': 'Edit Guest', 'email': 'edit-guest@example.com'}],
            'message': 'You are invited!',
            'subject': 'Test invitation',
        }, 200)
        assert len(deliver['results']) == 1
        # In test env without SMTP, the email channel reports 'queued'.
        assert deliver['results'][0]['status'] in {'queued', 'sent'}, f'got {deliver["results"][0]["status"]}'

        # Verify sent_at is set on the invitation.
        history = client.request(f'/api/invitations/{invite_id}/edit-history')
        assert history['sentAt'] is not None, f'sent_at should be set after delivery, got: {history}'

        # Save an edited document after send — should create an edit-history entry.
        edited_doc = dict(doc)
        edited_doc['fields'] = dict(doc['fields'])
        edited_doc['fields']['venue'] = 'Updated Venue (after send)'
        saved = client.request(f'/api/invitations/{invite_id}', 'PUT', {
            'document': edited_doc,
            'editReason': 'venue change after send',
        }, 200)
        assert saved.get('editedAfterSend') is True, f'expected editedAfterSend=True, got: {saved}'

        # Verify edit history now has 1 entry with the venue diff.
        history = client.request(f'/api/invitations/{invite_id}/edit-history')
        assert len(history['history']) == 1, f'expected 1 edit-history entry, got {len(history["history"])}'
        entry = history['history'][0]
        assert entry['reason'] == 'venue change after send', f'expected reason "venue change after send", got: {entry["reason"]}'
        # The diff should include the 'fields' key change.
        diff_paths = [d.get('path') for d in entry['diff']]
        assert 'fields' in diff_paths, f'expected fields in diff paths, got: {diff_paths}'
        # V54.4 — edited_after_send_at is set on the FIRST post-send edit and
        # surfaced via the edit-history endpoint so the host UI can render an
        # "Edited at {ts}" badge.
        assert history.get('editedAfterSendAt') is not None, \
            f'expected editedAfterSendAt to be set after first post-send edit, got: {history}'
        first_edit_ts = history['editedAfterSendAt']

        # Trigger a resend notification (SMTP not configured → 0 sent, but should not error).
        resend = client.request(f'/api/invitations/{invite_id}/resend-notification', 'POST',
                                 {'onlyViewed': False, 'message': 'We have updated the venue.'}, 200)
        # Without SMTP configured, sent count may be 0; that's OK.
        assert 'sent' in resend, f'expected sent count, got: {resend}'

        # Save again without sent_at — no new edit-history entry. (We'll just
        # verify the count remains stable since sent_at is already set.)
        history_before = client.request(f'/api/invitations/{invite_id}/edit-history')
        # No-op save: just verify the history endpoint still works after a second save.
        saved2 = client.request(f'/api/invitations/{invite_id}', 'PUT', {
            'document': edited_doc, 'editReason': 'no change',
        }, 200)
        history_after = client.request(f'/api/invitations/{invite_id}/edit-history')
        # The "no change" save should still record a history entry (diff is
        # empty in this case but the row is inserted).
        assert len(history_after['history']) >= len(history_before['history']), 'history should not shrink'
        # V54.4 — edited_after_send_at is NEVER overwritten: it stays pinned
        # to the timestamp of the FIRST post-send edit even after subsequent
        # saves. This is the contract that powers the public "Edited at {ts}"
        # badge on the guest-facing invitation page.
        assert history_after.get('editedAfterSendAt') == first_edit_ts, \
            f'editedAfterSendAt must not change after the first post-send edit; expected {first_edit_ts}, got {history_after.get("editedAfterSendAt")}'

        # List deliveries.
        deliveries = client.request(f'/api/invitations/{invite_id}/deliveries')
        assert deliveries['total'] >= 1, f'expected at least 1 delivery, got: {deliveries}'
        assert deliveries['deliveries'][0]['channel'] == 'email'

        print('P2A_POST_SEND_EDITING_TEST_PASSED')


if __name__ == '__main__':
    run()
