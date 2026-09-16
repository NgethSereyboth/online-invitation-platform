#!/usr/bin/env python3
"""V54.9 (sec-1, P1-A from ASVS L2 gap analysis) — Regression test for
reflected HTML injection in ``serve_public``.

Per ``docs/ROADMAP-V2.md`` §2.1 ("P1-A: Fix reflected HTML injection in
serve_public"), the slug from the URL was substituted into
``<meta content="...">`` and ``<link href="...">`` without
``html.escape(..., quote=True)``. CSP blocks script execution as a
last-line defense, but defense-in-depth is violated.

This test verifies that EVERY user-controlled value substituted into
``public.html`` is now HTML-escaped with ``quote=True``:

1. ``__INVITATION_TITLE__`` — host-controlled (``document.fields.names``),
   reflected in ``<title>`` text, ``og:title``, ``twitter:title``.
2. ``__INVITATION_DESCRIPTION__`` — host-controlled
   (``document.fields.message``), reflected in
   ``<meta name="description">``, ``og:description``,
   ``twitter:description``.
3. ``__INVITATION_SLUG__`` — attacker-controlled (URL path), reflected in
   ``<meta name="einvite-invitation-slug" content="...">`` and
   ``<link rel="canonical" href="/i/...">``. The slug arrives straight
   from ``self.path`` via the dispatcher at ``server.py`` L3237
   (``path.split("/", 2)[2]``) — no URL-decoding, no validation.

Attack scenarios
----------------

A. Host saves an invitation whose title is
   ``<script>alert("title-xss")</script>`` and description is
   ``"><img src=x onerror=alert("desc-xss")>``. The values are persisted
   in ``document_json`` (``validate_document`` does not sanitize plain
   string fields — only rich-text ``objects[].html``). When the published
   invitation is fetched at ``/i/<slug>``, the response HTML must contain
   ONLY the escaped forms — never the raw ``<script>`` or unescaped
   ``"><img`` substrings.

B. Attacker crafts a URL with raw HTML chars in the path:
   ``/i/"><script>alert(1)</script>``. Browsers normally percent-encode
   these characters, but a manual HTTP client (curl, raw socket, HTTP
   library that doesn't enforce encoding) can send them verbatim. The
   server must defend against this. We bypass ``urllib`` with a raw
   socket and verify the response contains ONLY the escaped form.

Run:

    cd /path/to/einvite-platform
    PYTHONPATH=tests:. python3 -m pytest tests/security_reflected_injection_test.py -v
    # or directly:
    PYTHONPATH=tests:. python3 tests/security_reflected_injection_test.py
"""
from __future__ import annotations
import html as html_module
import json
import socket
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

from v14_test_utils import app_server

ROOT = Path(__file__).resolve().parents[1]


class Client:
    """Thin JSON HTTP client bound to a single CookieJar + bearer token."""

    def __init__(self, base):
        self.base = base
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.token = ''

    def request(self, path, method='GET', body=None, expected=200, headers=None):
        payload = None if body is None else json.dumps(body).encode('utf-8')
        hdr = {'Accept': 'application/json', **(headers or {})}
        if payload is not None:
            hdr['Content-Type'] = 'application/json'
        if self.token:
            hdr['Authorization'] = f'Bearer {self.token}'
        req = urllib.request.Request(self.base + path, data=payload,
                                     method=method, headers=hdr)
        try:
            with self.opener.open(req, timeout=15) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
        if status != expected:
            raise AssertionError(
                f'{method} {path}: expected {expected}, got {status}: '
                f'{raw[:500]!r}')
        return json.loads(raw or b'{}')

    def get_text(self, path):
        """GET a path (urllib-encoded) and return the response body as text."""
        req = urllib.request.Request(self.base + path, method='GET')
        with self.opener.open(req, timeout=15) as response:
            return response.read().decode('utf-8', 'replace')


def raw_http_get(host, port, raw_path):
    """Send a raw HTTP request bypassing urllib's URL-encoding.

    The path is sent verbatim on the wire so that literal ``"``, ``<``, ``>``
    characters reach the dispatcher. ``urllib`` would percent-encode these
    (matching what a browser does), but a curl / raw socket / hand-rolled
    HTTP client can send them un-encoded — the server must defend against
    this case as defense-in-depth.
    """
    sock = socket.create_connection((host, port), timeout=15)
    try:
        request = (
            f'GET {raw_path} HTTP/1.1\r\n'
            f'Host: {host}:{port}\r\n'
            f'Connection: close\r\n'
            f'\r\n'
        )
        sock.sendall(request.encode('latin-1'))
        chunks = []
        while True:
            data = sock.recv(8192)
            if not data:
                break
            chunks.append(data)
        raw = b''.join(chunks)
    finally:
        sock.close()
    sep = raw.find(b'\r\n\r\n')
    if sep == -1:
        return 0, b''
    head = raw[:sep].decode('latin-1', 'replace')
    body = raw[sep + 4:]
    status_line = head.split('\r\n', 1)[0]
    try:
        status = int(status_line.split(' ', 2)[1])
    except (IndexError, ValueError):
        status = 0
    return status, body


def run():
    with app_server({
        'EINVITE_REQUIRE_EMAIL_VERIFICATION': '0',
        'EINVITE_ALLOW_NO_SCANNER': '1',
    }) as (_process, base, _data):
        # base = 'http://127.0.0.1:PORT'
        assert base.startswith('http://127.0.0.1:'), f'unexpected base: {base}'
        port = int(base.rsplit(':', 1)[1])
        host = '127.0.0.1'

        client = Client(base)
        stamp = int(time.time() * 1000)

        # ─── Scenario A: title + description reflected XSS ────────────────
        #
        # Host saves an invitation whose title and description contain raw
        # HTML attack payloads. ``validate_document`` does NOT sanitize
        # plain string fields (only rich-text ``objects[].html``), so the
        # raw payloads are persisted in ``document_json``. When the
        # published invitation is fetched at /i/<slug>, the response must
        # contain ONLY the HTML-escaped forms.
        attack_title = '<script>alert("title-xss")</script>'
        attack_desc = '"><img src=x onerror=alert("desc-xss")>'
        slug = f'sec-1-title-desc-{stamp}'

        registered = client.request('/api/auth/register', method='POST', body={
            'email': f'sec1-{stamp}@example.com',
            'password': 'strong-password-123',
        }, expected=201)
        client.token = registered.get('token', '')

        doc = {
            'schemaVersion': 13,
            'eventType': 'Wedding',
            'fields': {
                'names': attack_title,
                'message': attack_desc,
                'date': '2027-06-14',
                'venue': 'Test Venue',
            },
            'objects': {},
            'designPages': [],
            'sectionOrder': [],
            'settings': {'rsvpEnabled': False, 'wishesEnabled': False},
        }
        invitation = client.request('/api/invitations', method='POST', body={
            'slug': slug, 'document': doc,
        }, expected=201)
        invite_id = invitation['id']

        client.request(f'/api/invitations/{invite_id}/publish', method='POST',
                       body={'document': doc}, expected=201)

        page = client.get_text(f'/i/{slug}')

        # Title must be HTML-escaped in every context (<title>, og:title,
        # twitter:title). html.escape(s, quote=True) escapes & < > " '.
        escaped_title = html_module.escape(attack_title, quote=True)
        assert escaped_title in page, (
            f'expected escaped title {escaped_title!r} in response, '
            f'got (first 1000 chars): {page[:1000]!r}')
        assert attack_title not in page, (
            f'raw (unescaped) attack title leaked into HTML: '
            f'{attack_title!r}\nfirst 1000 chars: {page[:1000]!r}')

        # Description must be HTML-escaped in <meta name="description">,
        # og:description, twitter:description.
        escaped_desc = html_module.escape(attack_desc, quote=True)
        assert escaped_desc in page, (
            f'expected escaped description {escaped_desc!r} in response, '
            f'got (first 1000 chars): {page[:1000]!r}')
        assert attack_desc not in page, (
            f'raw (unescaped) attack description leaked into HTML: '
            f'{attack_desc!r}\nfirst 1000 chars: {page[:1000]!r}')

        # The specific dangerous substrings must not appear unescaped.
        assert 'alert("title-xss")</script>' not in page, (
            'raw <script>alert("title-xss")</script> leaked into HTML')
        assert 'onerror=alert("desc-xss")' not in page, (
            'raw onerror= handler leaked into HTML')

        # ─── Scenario B: slug reflected XSS via raw HTTP path ─────────────
        #
        # The slug arrives straight from the URL path (server.py L3237
        # dispatcher: ``path.split("/", 2)[2]``) — no URL-decoding, no
        # validation. ``urllib`` percent-encodes path chars, so we bypass
        # it with a raw socket to send literal HTML chars on the wire.
        attack_slug = '"><script>alert(1)</script>'
        raw_path = f'/i/{attack_slug}'
        status, body_bytes = raw_http_get(host, port, raw_path)
        assert status == 200, (
            f'expected 200 for raw-slug request, got {status}; '
            f'body (first 500): {body_bytes[:500]!r}')
        slug_page = body_bytes.decode('utf-8', 'replace')

        escaped_slug = html_module.escape(attack_slug, quote=True)
        # The escaped slug should appear at least twice in the response:
        # once in <meta name="einvite-invitation-slug" content="..."> and
        # once in <link rel="canonical" href="/i/...">.
        occurrences = slug_page.count(escaped_slug)
        assert occurrences >= 2, (
            f'expected escaped slug {escaped_slug!r} to appear at least '
            f'twice in response (meta content + link href), found '
            f'{occurrences} time(s); first 1200 chars: '
            f'{slug_page[:1200]!r}')

        # The raw attack payload must NOT appear anywhere in the HTML.
        # (public.html has a legitimate <script src="bundle-public-v15.js">
        # tag, so we check for the SPECIFIC attack substring rather than
        # the bare '<script>' token.)
        assert attack_slug not in slug_page, (
            f'raw (unescaped) attack slug leaked into HTML: '
            f'{attack_slug!r}\nfirst 1200 chars: {slug_page[:1200]!r}')
        assert 'alert(1)</script>' not in slug_page, (
            'raw <script>alert(1)</script> payload leaked into HTML')

        # The unescaped double-quote (") must not appear in the slug
        # reflection contexts (meta content + link href). We verify by
        # locating the <meta name="einvite-invitation-slug" content="...">
        # tag and confirming the attribute value is properly quoted.
        meta_opening = '<meta name="einvite-invitation-slug" content="'
        meta_idx = slug_page.find(meta_opening)
        assert meta_idx != -1, (
            f'could not find meta einvite-invitation-slug tag in response; '
            f'first 1200 chars: {slug_page[:1200]!r}')
        value_start = meta_idx + len(meta_opening)
        value_end = slug_page.find('"', value_start)
        assert value_end != -1, (
            'could not find closing quote of meta einvite-invitation-slug '
            'content attribute')
        meta_value = slug_page[value_start:value_end]
        assert meta_value == escaped_slug, (
            f'meta einvite-invitation-slug content should be {escaped_slug!r}, '
            f'got {meta_value!r}')

        # Same check for <link rel="canonical" href="/i/...">.
        link_opening = '<link rel="canonical" href="/i/'
        link_idx = slug_page.find(link_opening)
        assert link_idx != -1, (
            f'could not find <link rel="canonical"> tag in response; '
            f'first 1200 chars: {slug_page[:1200]!r}')
        href_start = link_idx + len(link_opening)
        href_end = slug_page.find('"', href_start)
        assert href_end != -1, (
            'could not find closing quote of <link rel="canonical"> href')
        href_value = slug_page[href_start:href_end]
        assert href_value == escaped_slug, (
            f'<link rel="canonical"> href should end with {escaped_slug!r}, '
            f'got {href_value!r}')

        print('SECURITY_REFLECTED_INJECTION_TEST_PASSED')


# pytest-compatible entry point.
def test_reflected_injection_in_serve_public():
    run()


if __name__ == '__main__':
    run()
