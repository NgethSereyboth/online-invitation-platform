#!/usr/bin/env python3
"""Phase 2a (V54.1) — Polls contract test.

End-to-end HTTP test: host creates a poll, guest votes, results hidden until
deadline (visibility=hidden_until_close), host sees live results, single-select
vote replacement, multi-select poll, poll deletion.
"""
from __future__ import annotations
import json
import time
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
                                     {'email': 'p2a-polls@example.com', 'password': 'strong-password-123'}, 201)
        client.token = registered.get('token', '')

        doc = {'schemaVersion': 13, 'eventType': 'Wedding',
               'fields': {'names': 'Poll Couple', 'date': '2027-04-14', 'venue': 'Poll Hall'},
               'objects': {}, 'designPages': [], 'sectionOrder': [],
               'settings': {'rsvpEnabled': False, 'wishesEnabled': False}}
        invitation = client.request('/api/invitations', 'POST', {'slug': 'p2a-polls-test', 'document': doc}, 201)
        invite_id = invitation['id']
        client.request(f'/api/invitations/{invite_id}/publish', 'POST', {'document': doc}, 201)

        # Create a poll with hidden_until_close visibility + a future deadline.
        future_ts = int(time.time() * 1000) + 3600_000  # 1h from now
        poll = client.request(f'/api/invitations/{invite_id}/polls', 'POST', {
            'question': 'Which dessert should we serve?',
            'options': [
                {'id': 'opt1', 'label': 'Chocolate cake'},
                {'id': 'opt2', 'label': 'Cheesecake'},
                {'id': 'opt3', 'label': 'Fruit tart'},
            ],
            'visibility': 'hidden_until_close',
            'multiSelect': False,
            'deadlineTs': future_ts,
        }, 201)
        assert poll['id'], 'poll id missing'
        assert poll['closed'] is False, 'poll should not be closed yet'

        # Guest votes (anonymous — provide email so single-select dedup works).
        vote = client.request(f'/api/invitations/{invite_id}/polls/{poll["id"]}/vote', 'POST',
                               {'optionIds': ['opt1'], 'name': 'Voter One', 'email': 'voter1@example.com'}, 201)
        assert len(vote['votes']) == 1

        # Single-select: voting again replaces the prior vote (same email).
        vote2 = client.request(f'/api/invitations/{invite_id}/polls/{poll["id"]}/vote', 'POST',
                                {'optionIds': ['opt2'], 'name': 'Voter One', 'email': 'voter1@example.com'}, 201)
        assert len(vote2['votes']) == 1

        # Guest fetches results: should be hidden (poll still open + visibility=hidden_until_close).
        # Use a guest client (no Authorization header).
        guest_client = Client(base)
        guest_client.token = ''  # explicitly unauthenticated
        results = guest_client.request(f'/api/invitations/{invite_id}/polls/{poll["id"]}/results')
        assert results.get('resultsVisible') is False, f'guest should not see results yet, got: {results}'

        # Host fetches results: should see counts.
        host_results = client.request(f'/api/invitations/{invite_id}/polls/{poll["id"]}/results',
                                       headers={'Authorization': f'Bearer {client.token}'})
        assert host_results.get('totalVotes', 0) == 1, f'expected 1 total vote, got: {host_results.get("totalVotes")}'
        opt2 = next(o for o in host_results['options'] if o['id'] == 'opt2')
        assert opt2['votes'] == 1, f'expected opt2 to have 1 vote, got: {opt2.get("votes")}'

        # Create a multi-select poll.
        multi_poll = client.request(f'/api/invitations/{invite_id}/polls', 'POST', {
            'question': 'Which activities do you want?',
            'options': [{'id': 'a1', 'label': 'Photo booth'}, {'id': 'a2', 'label': 'Dance floor'}, {'id': 'a3', 'label': 'Live band'}],
            'visibility': 'live', 'multiSelect': True, 'deadlineTs': None,
        }, 201)
        assert multi_poll['multiSelect'] is True
        # Multi-select vote with 2 options.
        multi_vote = client.request(f'/api/invitations/{invite_id}/polls/{multi_poll["id"]}/vote', 'POST',
                                     {'optionIds': ['a1', 'a3'], 'name': 'Voter Two'}, 201)
        assert len(multi_vote['votes']) == 2

        # Live-visibility poll: guests can see results immediately.
        live_results = client.request(f'/api/invitations/{invite_id}/polls/{multi_poll["id"]}/results')
        assert live_results['totalVotes'] == 2, f'expected 2 total votes, got: {live_results["totalVotes"]}'

        # Single-select poll rejects multi-option votes.
        try:
            client.request(f'/api/invitations/{invite_id}/polls/{poll["id"]}/vote', 'POST',
                            {'optionIds': ['opt1', 'opt2'], 'name': 'Greedy Voter'}, 400)
        except AssertionError as exc:
            raise AssertionError(f'Expected 400 for multi-option on single-select, got: {exc}')

        # Delete the multi-select poll.
        deleted = client.request(f'/api/invitations/{invite_id}/polls/{multi_poll["id"]}', 'DELETE', expected=200)
        assert deleted['deleted'] is True
        polls = client.request(f'/api/invitations/{invite_id}/polls')
        assert len(polls) == 1, f'expected 1 remaining poll, got {len(polls)}'

        print('P2A_POLLS_TEST_PASSED')


if __name__ == '__main__':
    run()
