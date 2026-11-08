#!/usr/bin/env python3
"""Loopback-only, non-destructive policy proxy for the authenticated DAST scan.

ZAP targets this proxy, never the fixture server directly. The proxy:

* allows GET, HEAD and OPTIONS for read-only exploration and active scanning;
* allows exactly one POST, ``/api/auth/login``, which is rate-limited and
  non-destructive;
* rejects PUT, PATCH, DELETE and every other POST with 405 before forwarding;
* forwards the configured session cookie/CSRF headers from ZAP's replacer;
* forces ``Host`` and ``Origin`` to the fixture backend so the app's
  same-origin/CSRF checks see a matching local origin.

The blocked-request log is an artifact, so a reviewer can see every method the
scanner attempted but the fixture refused.
"""
from __future__ import annotations

import argparse
import http.client
import http.server
import json
import sys
import threading
import time
import urllib.parse
from pathlib import Path


ALLOWED_METHODS = {"GET", "HEAD", "OPTIONS"}
ALLOWED_POST_PATHS = {"/api/auth/login"}
MAX_BODY = 64 * 1024
HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


class PolicyProxy(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    backend_host = ""
    backend_port = 0
    backend_origin = ""
    blocked_log = Path("/tmp/dast-blocked-requests.log")

    def log_message(self, fmt, *args):
        # Keep the proxy log useful without dumping request headers, which may
        # contain the disposable session cookie.
        super().log_message("%s", fmt % args)

    def _blocked(self, method, path, status, reason):
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        safe_path = path.replace("\t", "%09").replace("\r", "").replace("\n", "")[:500]
        line = f"{timestamp}\t{method}\t{status}\t{safe_path}\t{reason}\n"
        with self.blocked_log.open("a", encoding="utf-8") as handle:
            handle.write(line)
        body = json.dumps({"error": reason, "code": "dast_policy_blocked"}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(body)

    def _handle(self):
        method = self.command.upper()
        path = urllib.parse.urlsplit(self.path).path
        if method not in ALLOWED_METHODS and not (
            method == "POST" and path in ALLOWED_POST_PATHS
        ):
            self._blocked(method, self.path, 405, "method/path not in DAST allowlist")
            return

        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            self._blocked(method, self.path, 400, "invalid content-length")
            return
        if length < 0 or length > MAX_BODY:
            self._blocked(method, self.path, 413, "request body exceeds DAST limit")
            return
        body = self.rfile.read(length) if length else None

        forwarded = {}
        for name in (
            "Accept",
            "Content-Type",
            "Cookie",
            "User-Agent",
            "X-CSRF-Token",
        ):
            value = self.headers.get(name)
            if value:
                forwarded[name] = value
        forwarded["Host"] = f"{self.backend_host}:{self.backend_port}"
        forwarded["Origin"] = self.backend_origin

        connection = http.client.HTTPConnection(
            self.backend_host, self.backend_port, timeout=30
        )
        try:
            connection.request(method, self.path, body=body, headers=forwarded)
            response = connection.getresponse()
            data = response.read()
            self.send_response(response.status, response.reason)
            for name, value in response.getheaders():
                if name.lower() in HOP_HEADERS:
                    continue
                self.send_header(name.replace("\r", "").replace("\n", ""), value.replace("\r", "").replace("\n", ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(data)
        except Exception as exc:  # noqa: BLE001 - proxy reports a 502 to the scanner
            self._blocked(method, self.path, 502, f"backend error: {type(exc).__name__}")
        finally:
            connection.close()

    do_GET = _handle
    do_HEAD = _handle
    do_OPTIONS = _handle
    do_POST = _handle

    def do_PUT(self):
        self._blocked("PUT", self.path, 405, "method not in DAST allowlist")

    def do_PATCH(self):
        self._blocked("PATCH", self.path, 405, "method not in DAST allowlist")

    def do_DELETE(self):
        self._blocked("DELETE", self.path, 405, "method not in DAST allowlist")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--blocked-log", required=True)
    args = parser.parse_args()

    parsed = urllib.parse.urlsplit(args.backend)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        print("Backend must be a loopback HTTP origin", file=sys.stderr)
        return 2
    if not parsed.port:
        print("Backend must include an explicit port", file=sys.stderr)
        return 2

    Handler.backend_host = parsed.hostname
    Handler.backend_port = parsed.port
    Handler.backend_origin = f"http://{parsed.hostname}:{parsed.port}"
    Handler.blocked_log = Path(args.blocked_log)
    Handler.blocked_log.parent.mkdir(parents=True, exist_ok=True)

    server = PolicyProxy(("127.0.0.1", args.port), Handler)
    print(f"SAFE_PROXY_READY http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
