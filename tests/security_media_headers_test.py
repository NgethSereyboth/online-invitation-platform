from __future__ import annotations

from src.python import server as _server


class _Headers(list):
    def get(self, name: str, default: str = "") -> str:
        return default


class _FakeHandler:
    @staticmethod
    def _safe_inline_filename(filename):
        return _server.Handler._safe_inline_filename(filename)

    def __init__(self) -> None:
        self.headers = _Headers()
        self.status = None
        self.written = b""

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, name: str, value: str) -> None:
        if "\r" in value or "\n" in value:
            raise AssertionError("header value contains a raw line break")
        self.headers.append((name, value))

    def end_headers(self) -> None:
        pass

    def wfile_write(self, body: bytes) -> None:
        self.written = body

    @property
    def wfile(self):
        class _Writer:
            def __init__(self, handler):
                self.handler = handler

            def write(self, body):
                self.handler.written = body

        return _Writer(self)

    def get_header(self, name: str) -> str:
        return next((value for key, value in self.headers if key.lower() == name.lower()), "")


def _run(helper, *args, **kwargs) -> _FakeHandler:
    handler = _FakeHandler()
    helper(handler, *args, **kwargs)
    return handler


def test_binary_helpers_quote_escape_attacker_controlled_filenames():
    raw_filename = 'photo"; filename*=UTF-8\'\'evil.png\r\nX-Injected: yes'
    body = b"image bytes"

    binary = _run(
        _server.Handler.send_binary,
        200,
        body,
        "image/png",
        filename=raw_filename,
    )
    media = _run(
        _server.Handler.send_media_binary,
        200,
        body,
        "image/png",
        "authenticated",
        filename=raw_filename,
    )

    for response in (binary, media):
        disposition = response.get_header("Content-Disposition")
        assert disposition.startswith('inline; filename="'), disposition
        assert disposition.count('"') == 2, disposition
        assert disposition.count(";") == 1, disposition
        assert "\r" not in disposition and "\n" not in disposition, disposition
        assert not any(key.lower() == "x-injected" for key, _ in response.headers)
        assert sum(key.lower() == "content-disposition" for key, _ in response.headers) == 1
        assert response.written == body
