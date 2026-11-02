#!/usr/bin/env python3
"""Serve the freshly built Sites bundle with the local Python backend.

The production Worker serves `artifacts/sites-public` and proxies dynamic
routes to the PC backend. This is the same arrangement on loopback, so the
round-4 Playwright sweep exercises the phase-10 bundle rather than the source
mirror. Static requests are served from the bundle; API, published-invitation,
management-screen, upload and template-pack requests are proxied.

Run with the backend already listening, for example:

    .venv/bin/python bugs/round-4/serve_bundle.py \
        --port 4180 --backend 127.0.0.1:4181
"""
from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import posixpath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "artifacts" / "sites-public"
PROXY_PREFIXES = (
    "/api", "/uploads/", "/i/", "/invitations/", "/_marketplace/",
    "/assets/template-pack/",
)
BACKEND = ("127.0.0.1", 4181)


def needs_proxy(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in PROXY_PREFIXES)


class Handler(BaseHTTPRequestHandler):
    server_version = "EInviteRound4/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the terminal quiet; request logs are noise
        return

    def _proxy(self) -> None:
        parsed = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in {"host", "connection", "content-length"}}
        # The browser's Host is the proxy origin; preserve it so the backend's
        # same-origin/CSRF guard sees the origin the user actually used.
        headers["Host"] = self.headers.get("Host", f"{self.server.server_name}:{self.server.server_port}")
        headers["X-Forwarded-Proto"] = "http"
        headers["X-Forwarded-Host"] = headers["Host"]
        if length:
            headers["Content-Length"] = str(length)
        conn = http.client.HTTPConnection(BACKEND[0], BACKEND[1], timeout=120)
        try:
            conn.request(self.command, parsed.path + (("?" + parsed.query) if parsed.query else ""),
                         body=body, headers=headers)
            upstream = conn.getresponse()
            payload = upstream.read()
            self.send_response(upstream.status, upstream.reason)
            for name, value in upstream.getheaders():
                if name.lower() not in {"connection", "transfer-encoding", "content-length"}:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        except Exception as exc:
            payload = json.dumps({"error": "backend_unreachable", "detail": str(exc)[:200]}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        finally:
            conn.close()

    def _static(self) -> bool:
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        if path == "/":
            rel = "index.html"
        else:
            rel = path.lstrip("/")
        if not rel or ".." in Path(rel).parts:
            return False
        candidate = BUNDLE / rel
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file() and not Path(rel).suffix:
            html = (BUNDLE / (rel + ".html"))
            if html.is_file():
                candidate = html
        if not candidate.is_file():
            return False
        payload = candidate.read_bytes()
        ctype = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)
        return True

    def _handle(self) -> None:
        if needs_proxy(urlsplit(self.path).path):
            return self._proxy()
        if self.command in {"GET", "HEAD"} and self._static():
            return
        # The production Worker falls back to the backend for HTML requests
        # whose asset is absent, which preserves the 404 page/status contract.
        if self.command in {"GET", "HEAD"} and "text/html" in (self.headers.get("Accept") or "").lower():
            return self._proxy()
        payload = b'{"error":"Not found"}'
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    do_GET = _handle
    do_HEAD = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle
    do_DELETE = _handle
    do_OPTIONS = _handle


def main() -> None:
    global BACKEND
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4180)
    parser.add_argument("--backend", default="127.0.0.1:4181")
    args = parser.parse_args()
    host, port = args.backend.rsplit(":", 1)
    BACKEND = (host, int(port))
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"ROUND4_BUNDLE_SERVER http://127.0.0.1:{args.port} root={BUNDLE} backend={BACKEND[0]}:{BACKEND[1]}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
