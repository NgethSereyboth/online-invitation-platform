"""Generated header-injection coverage for response and cookie headers.

Hypothesis supplies CR, LF, CRLF, NUL, quotes, semicolons and Unicode line
separators around ordinary text. The assertions are about emitted header
values, not implementation details: no raw line break or NUL may survive, a
Content-Disposition must be emitted once, and ordinary filenames must not be
rewritten.
"""
from __future__ import annotations

import string

from hypothesis import given, settings, strategies as st

from src.python import server as _server

DANGEROUS = ["\r", "\n", "\r\n", "\x00", "\u2028", "\u2029", '"', ";", "\\"]
TOKEN_ALPHABET = string.ascii_letters + string.digits + "-_"


@st.composite
def hostile_text(draw):
    alphabet = st.characters(blacklist_categories=("Cs",))
    left = draw(st.text(alphabet=alphabet, max_size=24))
    breaks = draw(st.lists(st.sampled_from(DANGEROUS), min_size=1, max_size=3))
    right = draw(st.text(alphabet=alphabet, max_size=24))
    return left + "".join(breaks) + right


class _Headers:
    def get(self, name, default=""):
        return default


class _Writer:
    def __init__(self, handler):
        self.handler = handler

    def write(self, body):
        self.handler.body += body


class _Handler:
    @staticmethod
    def _safe_inline_filename(filename):
        return _server.Handler._safe_inline_filename(filename)

    def __init__(self):
        self.headers = _Headers()
        self.sent = []
        self.status = None
        self.body = b""

    @property
    def wfile(self):
        return _Writer(self)

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        assert "\r" not in value, (name, value)
        assert "\n" not in value, (name, value)
        assert "\x00" not in value, (name, value)
        self.sent.append((name, value))

    def end_headers(self):
        pass

    def safe_write(self, body):
        self.body += body
        return True


def _responses(filename):
    payload = b"generated header probe"
    for helper, args in (
        (_server.Handler.send_download, (payload, "text/plain", filename)),
        (_server.Handler.send_binary, (200, payload, "image/png")),
        (_server.Handler.send_media_binary, (200, payload, "image/png", "public")),
    ):
        handler = _Handler()
        if helper is _server.Handler.send_download:
            helper(handler, *args)
        else:
            helper(handler, *args, filename=filename)
        yield handler


def test_safe_header_value_removes_nul():
    assert "\x00" not in _server.safe_header_value("before\x00after")


@settings(max_examples=100, deadline=None)
@given(hostile_text())
def test_safe_header_value_has_no_raw_line_break_or_nul(value):
    cleaned = _server.safe_header_value(value)
    assert "\r" not in cleaned, repr(value)
    assert "\n" not in cleaned, repr(value)
    assert "\x00" not in cleaned, repr(value)


@settings(max_examples=100, deadline=None)
@given(hostile_text())
def test_location_value_has_no_raw_line_break_or_nul(value):
    cleaned = _server.safe_header_value("https://example.test/i/" + value)
    assert "\r" not in cleaned, repr(value)
    assert "\n" not in cleaned, repr(value)
    assert "\x00" not in cleaned, repr(value)


@settings(max_examples=100, deadline=None)
@given(hostile_text())
def test_safe_filename_is_ascii_single_line(value):
    cleaned = _server.Handler._safe_inline_filename(value)
    assert cleaned
    assert len(cleaned) <= 180
    assert cleaned.isascii()
    for char in "\r\n\x00\"\\;":
        assert char not in cleaned, (repr(value), repr(cleaned))


def test_ordinary_filename_is_unchanged():
    assert _server.Handler._safe_inline_filename("photo-2026.png") == "photo-2026.png"


@settings(max_examples=60, deadline=None)
@given(hostile_text())
def test_response_headers_are_single_line(value):
    for response in _responses(value):
        dispositions = [v for k, v in response.sent if k.lower() == "content-disposition"]
        assert len(dispositions) == 1, response.sent
        disposition = dispositions[0]
        assert disposition.startswith(("inline; filename=\"", "attachment; filename=\"")), disposition
        assert disposition.count('"') == 2, disposition
        assert disposition.count(";") == 1, disposition
        for name, header in response.sent:
            assert "\r" not in header, (name, header)
            assert "\n" not in header, (name, header)
            assert "\x00" not in header, (name, header)
        assert response.body == b"generated header probe"


@settings(max_examples=80, deadline=None)
@given(
    st.text(alphabet=TOKEN_ALPHABET, min_size=1, max_size=80),
    st.text(alphabet=TOKEN_ALPHABET, min_size=1, max_size=80),
)
def test_session_cookie_headers_stay_single_line(token, csrf):
    for cookie in _server.Handler._session_cookie(token, csrf, 3600):
        assert "\r" not in cookie and "\n" not in cookie and "\x00" not in cookie


@settings(max_examples=80, deadline=None)
@given(st.text(alphabet=TOKEN_ALPHABET, min_size=1, max_size=80))
def test_impersonation_cookie_header_stays_single_line(value):
    cookie = _server.Handler._impersonation_cookie(object(), value)
    assert "\r" not in cookie and "\n" not in cookie and "\x00" not in cookie
